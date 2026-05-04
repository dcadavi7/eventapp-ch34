import json
import os
import logging
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

TABLE_NAME = os.environ.get('TABLE_NAME')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'lab')


def handler(event, context):
    """
    Handler para solicitar un reporte de asistencia.
    POST /events/{id}/reports → encola mensaje en SQS FIFO para procesamiento asíncrono.
    """
    logger.info(f"Request report: {json.dumps(event)}")

    http_method = event.get('httpMethod')
    if http_method != 'POST':
        return build_response(405, {'message': 'Método no permitido'})

    path_parameters = event.get('pathParameters') or {}
    event_id = path_parameters.get('id')

    if not event_id:
        return build_response(400, {'message': 'El ID del evento es requerido'})

    try:
        body = json.loads(event.get('body') or '{}')
    except Exception:
        return build_response(400, {'message': 'JSON body inválido'})

    requester_email = body.get('requesterEmail', '').strip()
    if not requester_email:
        return build_response(400, {'message': 'El campo requesterEmail es requerido'})

    # Verificar que el evento existe
    table = dynamodb.Table(TABLE_NAME)
    item = table.get_item(Key={'PK': f"EVENT#{event_id}", 'SK': 'METADATA'}).get('Item')
    if not item:
        return build_response(404, {'message': 'Evento no encontrado'})

    try:
        queue_name = f"EventReportsQueue-{ENVIRONMENT}.fifo"
        queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']

        message_payload = json.dumps({
            'eventId': event_id,
            'eventName': item.get('name', event_id),
            'requesterEmail': requester_email,
            'requestedAt': datetime.now().isoformat()
        })

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message_payload,
            MessageGroupId=f"event-{event_id}"
        )
        logger.info(f"Solicitud de reporte encolada para evento {event_id} — solicitante: {requester_email}")

        return build_response(202, {
            'message': 'Solicitud de reporte encolada. Recibirás el reporte en tu correo en breve.'
        })

    except ClientError as e:
        logger.error(f"Error encolando solicitud de reporte: {e}")
        return build_response(500, {'message': 'Error interno al procesar la solicitud'})


def build_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }