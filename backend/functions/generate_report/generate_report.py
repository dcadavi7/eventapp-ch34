import json
import os
import csv
import io
import logging
import boto3
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError
from botocore.config import Config
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
s3 = boto3.client('s3', region_name=AWS_REGION, config=Config(signature_version='s3v4'))
ses = boto3.client('ses', region_name=AWS_REGION)

TABLE_NAME = os.environ.get('TABLE_NAME')
REPORTS_BUCKET = os.environ.get('REPORTS_BUCKET')
SES_FROM_EMAIL = os.environ.get('SES_FROM_EMAIL')

PRESIGNED_URL_TTL = 86400  # 24 horas


def handler(event, context):
    """
    Handler disparado por SQS FIFO (EventReportsQueue).
    Genera un CSV de asistentes, lo sube a S3 y envía al solicitante un presigned URL.
    """
    logger.info(f"Procesando {len(event.get('Records', []))} solicitudes de reporte.")

    for record in event.get('Records', []):
        try:
            message = json.loads(record['body'])
            event_id = message.get('eventId')
            event_name = message.get('eventName', event_id)
            requester_email = message.get('requesterEmail')

            if not event_id:
                logger.error("Mensaje sin eventId, descartando.")
                continue

            logger.info(f"Generando reporte para evento '{event_name}' ({event_id})")

            # 1. Consultar todos los asistentes
            table = dynamodb.Table(TABLE_NAME)
            attendees = get_all_attendees(table, event_id)
            logger.info(f"Asistentes encontrados: {len(attendees)}")

            # 2. Generar CSV en memoria
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(['Nombre', 'Correo', 'Fecha de registro'])
            for att in attendees:
                writer.writerow([
                    att.get('name', ''),
                    att.get('email', ''),
                    att.get('registeredAt', '')
                ])
            csv_content = csv_buffer.getvalue()

            # 3. Subir CSV a S3
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"reports/{event_id}/{timestamp}_asistentes.csv"
            s3.put_object(
                Bucket=REPORTS_BUCKET,
                Key=s3_key,
                Body=csv_content.encode('utf-8'),
                ContentType='text/csv; charset=utf-8',
                ContentDisposition=f'attachment; filename="reporte_{event_id}_{timestamp}.csv"'
            )
            logger.info(f"Reporte subido: s3://{REPORTS_BUCKET}/{s3_key}")

            # 4. Generar presigned URL (válida 24 h)
            presigned_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': REPORTS_BUCKET, 'Key': s3_key},
                ExpiresIn=PRESIGNED_URL_TTL
            )

            # 5. Notificar al solicitante por correo
            if requester_email and SES_FROM_EMAIL:
                send_report_email(requester_email, event_name, len(attendees), presigned_url)

        except Exception as e:
            logger.error(f"Error procesando solicitud de reporte: {e}")
            raise e  # SQS reintentará el mensaje

    return {'status': 'done'}


def get_all_attendees(table, event_id):
    """Consulta todos los registros USER# para un evento, con paginación."""
    attendees = []
    try:
        response = table.query(
            KeyConditionExpression=Key('PK').eq(f"EVENT#{event_id}") & Key('SK').begins_with("USER#")
        )
        attendees.extend(response.get('Items', []))
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression=Key('PK').eq(f"EVENT#{event_id}") & Key('SK').begins_with("USER#"),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            attendees.extend(response.get('Items', []))
    except Exception as e:
        logger.error(f"Error consultando asistentes del evento {event_id}: {e}")
    return attendees


def send_report_email(to_email, event_name, attendee_count, presigned_url):
    """Envía el correo con el enlace de descarga del reporte."""
    try:
        subject = f"Reporte de asistencia listo: {event_name}"
        html_body = (
            f"<h1>Reporte de Asistencia</h1>"
            f"<p>El reporte del evento <b>{event_name}</b> ha sido generado.</p>"
            f"<ul>"
            f"<li>Total de asistentes registrados: <b>{attendee_count}</b></li>"
            f"</ul>"
            f"<p><a href='{presigned_url}' style='padding:10px 20px;background:#4f46e5;color:white;text-decoration:none;border-radius:6px;'>Descargar reporte CSV</a></p>"
            f"<p><small>El enlace es válido por 24 horas.</small></p>"
        )
        text_body = (
            f"Reporte listo para el evento: {event_name}\n"
            f"Total asistentes: {attendee_count}\n"
            f"Descarga: {presigned_url}\n"
            f"(Válido por 24 horas)"
        )
        ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': text_body}
                }
            }
        )
        logger.info(f"Correo de reporte enviado a {to_email}")
    except ClientError as e:
        logger.error(f"Error enviando correo de reporte a {to_email}: {e.response['Error']['Message']}")