import json
import os
import logging
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ.get('TABLE_NAME')
SES_FROM_EMAIL = os.environ.get('SES_FROM_EMAIL')

BRAND_COLOR = '#4f46e5'
BRAND_NAME  = 'EventApp'


def get_event_details(event_id):
    """Obtiene nombre, fecha y lugar del evento desde DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_NAME)
        result = table.get_item(Key={'PK': f"EVENT#{event_id}", 'SK': 'METADATA'})
        item = result.get('Item', {})
        return {
            'name':     item.get('name', f'Evento {event_id}'),
            'date':     item.get('startDate', ''),
            'location': item.get('location', ''),
        }
    except Exception as e:
        logger.error(f"Error obteniendo detalles del evento {event_id}: {e}")
        return {'name': f'Evento {event_id}', 'date': '', 'location': ''}


def get_attendee_emails(event_id):
    """Consulta en DynamoDB todos los asistentes registrados para un evento."""
    table = dynamodb.Table(TABLE_NAME)
    emails = []
    try:
        response = table.query(
            KeyConditionExpression=Key('PK').eq(f"EVENT#{event_id}") & Key('SK').begins_with("USER#")
        )
        for item in response.get('Items', []):
            if 'email' in item:
                emails.append(item['email'])

        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression=Key('PK').eq(f"EVENT#{event_id}") & Key('SK').begins_with("USER#"),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response.get('Items', []):
                if 'email' in item:
                    emails.append(item['email'])

    except Exception as e:
        logger.error(f"Error consultando asistentes para {event_id}: {e}")

    return emails


def email_wrapper(content_html):
    """Envuelve el contenido en un layout de correo consistente."""
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#f8fafc;border-radius:12px;overflow:hidden;">
      <div style="background:{BRAND_COLOR};padding:28px 32px;">
        <h1 style="color:white;margin:0;font-size:22px;letter-spacing:-0.5px;">{BRAND_NAME}</h1>
        <p style="color:rgba(255,255,255,0.75);margin:4px 0 0;font-size:13px;">Gestión de Eventos</p>
      </div>
      <div style="background:white;padding:32px;">
        {content_html}
      </div>
      <div style="padding:20px 32px;text-align:center;">
        <p style="color:#94a3b8;font-size:12px;margin:0;">
          Este correo fue enviado automáticamente por {BRAND_NAME}.<br>
          Por favor no respondas a este mensaje.
        </p>
      </div>
    </div>
    """


MESES = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']

def format_date_cot(iso_string):
    """Convierte un ISO UTC a fecha legible en hora de Colombia (UTC-5)."""
    if not iso_string:
        return ''
    try:
        from datetime import timezone, timedelta
        from datetime import datetime as dt
        COT = timezone(timedelta(hours=-5))
        utc_dt = dt.fromisoformat(iso_string.replace('Z', '+00:00'))
        local = utc_dt.astimezone(COT)
        hora = local.strftime('%I:%M %p').lstrip('0')  # "8:07 PM"
        return f"{local.day} de {MESES[local.month - 1]} de {local.year}, {hora} (hora de Colombia)"
    except Exception:
        return iso_string


def event_info_block(evt):
    """Bloque HTML con los datos del evento (nombre, fecha, lugar)."""
    rows = f"<tr><td style='color:#64748b;padding:6px 0;font-size:14px;'>Evento</td><td style='font-weight:600;font-size:14px;padding:6px 0 6px 16px;'>{evt['name']}</td></tr>"
    if evt['date']:
        fecha_legible = format_date_cot(evt['date'])
        rows += f"<tr><td style='color:#64748b;padding:6px 0;font-size:14px;'>Fecha</td><td style='font-weight:600;font-size:14px;padding:6px 0 6px 16px;'>{fecha_legible}</td></tr>"
    if evt['location']:
        rows += f"<tr><td style='color:#64748b;padding:6px 0;font-size:14px;'>Lugar</td><td style='font-weight:600;font-size:14px;padding:6px 0 6px 16px;'>{evt['location']}</td></tr>"
    return f"""
    <table style="border-collapse:collapse;background:#f1f5f9;border-radius:8px;padding:16px;width:100%;margin:20px 0;">
      <tbody style="padding:16px;">{rows}</tbody>
    </table>
    """


def send_email(to_addresses, subject, html_body):
    """Envía el correo usando Amazon SES."""
    if not to_addresses:
        logger.info("No hay destinatarios para enviar el correo.")
        return

    full_html = email_wrapper(html_body)
    import re
    plain_text = re.sub(r'<[^>]+>', '', html_body).strip()

    try:
        response = ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={
                'ToAddresses': to_addresses if isinstance(to_addresses, list) else [to_addresses]
            },
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': full_html},
                    'Text': {'Data': plain_text}
                }
            }
        )
        logger.info(f"Correo enviado. MessageId: {response['MessageId']}")
    except ClientError as e:
        logger.error(f"Error de SES al enviar correo: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Error inesperado al enviar correo: {str(e)}")


def handler(event, context):
    """
    Handler disparado por SQS para enviar notificaciones.
    """
    logger.info(f"Procesando batch de {len(event['Records'])} mensajes SQS.")

    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            action          = message.get('action')
            event_id        = message.get('eventId')
            recipient_email = message.get('recipientEmail')

            logger.info(f"Acción: {action}, Evento: {event_id}")

            # 1. Registro de asistente — bienvenida
            if action == 'ASSISTANT_REGISTERED':
                attendee_name = message.get('name', 'Asistente')
                evt = get_event_details(event_id)
                subject = f"¡Tu registro está confirmado — {evt['name']}!"
                body = f"""
                <h2 style="color:#1e293b;margin:0 0 8px;">¡Hola, {attendee_name}! 🎉</h2>
                <p style="color:#475569;margin:0 0 4px;">Tu registro ha sido confirmado exitosamente.</p>
                {event_info_block(evt)}
                <p style="color:#475569;">Te esperamos. Recibirás recordatorios antes del evento.</p>
                """
                send_email(recipient_email, subject, body)

            # 2. Evento cancelado — aviso a todos
            elif action == 'EVENT_CANCELLED':
                evt = get_event_details(event_id)
                subject = f"Aviso importante: {evt['name']} ha sido cancelado"
                body = f"""
                <h2 style="color:#dc2626;margin:0 0 8px;">Evento cancelado</h2>
                <p style="color:#475569;">Lamentamos informarte que el siguiente evento ha sido cancelado:</p>
                {event_info_block(evt)}
                <p style="color:#475569;">Si tienes preguntas, comunícate directamente con el organizador.<br>
                Disculpa los inconvenientes causados.</p>
                """
                recipients = get_attendee_emails(event_id)
                if recipient_email and recipient_email not in recipients:
                    recipients.append(recipient_email)
                if recipients:
                    send_email(recipients, subject, body)

            # 3. Evento finalizado — agradecimiento
            elif action == 'EVENT_COMPLETED':
                evt = get_event_details(event_id)
                subject = f"¡Gracias por asistir a {evt['name']}!"
                body = f"""
                <h2 style="color:#1e293b;margin:0 0 8px;">¡Gracias por acompañarnos! 🙌</h2>
                <p style="color:#475569;">El evento ha concluido. Esperamos que haya sido una gran experiencia.</p>
                {event_info_block(evt)}
                <p style="color:#475569;">Hasta la próxima. ¡Estén atentos a nuevos eventos!</p>
                """
                recipients = get_attendee_emails(event_id)
                if recipients:
                    send_email(recipients, subject, body)

            # 4. Recordatorio automático
            elif action == 'SEND_REMINDER' and event_id:
                hours_left = message.get('hours_left', '?')
                evt = get_event_details(event_id)
                subject = f"Recordatorio: {evt['name']} comienza en {hours_left} horas"
                body = f"""
                <h2 style="color:#1e293b;margin:0 0 8px;">⏰ ¡Tu evento está por comenzar!</h2>
                <p style="color:#475569;">Te recordamos que el siguiente evento comienza en aproximadamente <strong>{hours_left} horas</strong>:</p>
                {event_info_block(evt)}
                <p style="color:#475569;">Asegúrate de llegar a tiempo. ¡Te esperamos!</p>
                """
                recipients = get_attendee_emails(event_id)
                if recipients:
                    send_email(recipients, subject, body)

            # 5. Notificación masiva del organizador
            elif action == 'MASS_NOTIFICATION' and event_id:
                evt = get_event_details(event_id)
                custom_subject = message.get('subject', 'Mensaje del organizador')
                custom_body_text = message.get('messageBody', '')
                subject = f"{custom_subject} — {evt['name']}"
                body = f"""
                <h2 style="color:#1e293b;margin:0 0 8px;">{custom_subject}</h2>
                {event_info_block(evt)}
                <div style="background:#f8fafc;border-left:4px solid {BRAND_COLOR};padding:16px;border-radius:0 8px 8px 0;margin:16px 0;">
                  <p style="color:#334155;margin:0;white-space:pre-line;">{custom_body_text}</p>
                </div>
                <p style="color:#94a3b8;font-size:13px;">— El equipo organizador</p>
                """
                recipients = get_attendee_emails(event_id)
                if recipients:
                    send_email(recipients, subject, body)

            # 6. Actualización o eliminación del evento
            elif event_id and action in ['EVENT_UPDATED', 'EVENT_DELETED']:
                evt = get_event_details(event_id)
                if action == 'EVENT_DELETED':
                    subject = f"El evento {evt['name']} ha sido eliminado"
                    body = f"""
                    <h2 style="color:#1e293b;margin:0 0 8px;">Evento eliminado</h2>
                    <p style="color:#475569;">El siguiente evento ha sido eliminado de la plataforma:</p>
                    {event_info_block(evt)}
                    <p style="color:#475569;">Si tienes preguntas, contacta al organizador.</p>
                    """
                else:
                    subject = f"Actualización en {evt['name']}"
                    body = f"""
                    <h2 style="color:#1e293b;margin:0 0 8px;">El evento ha sido actualizado</h2>
                    <p style="color:#475569;">Se han realizado cambios en el siguiente evento. Te recomendamos verificar los nuevos detalles:</p>
                    {event_info_block(evt)}
                    <p style="color:#475569;">Si tienes dudas, contacta al organizador.</p>
                    """

                recipients = message.get('attendeeEmails')
                if recipients is None:
                    recipients = get_attendee_emails(event_id)
                if recipient_email and recipient_email not in recipients:
                    recipients.append(recipient_email)
                if recipients:
                    send_email(recipients, subject, body)

            else:
                logger.warning(f"Mensaje SQS no reconocido o incompleto: {message}")

        except Exception as e:
            logger.error(f"Error procesando mensaje SQS: {e}")
            raise e

    return {'status': 'done'}