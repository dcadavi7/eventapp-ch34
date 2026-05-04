import json
import os
import logging
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.client('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')

def handler(event, context):
    """
    Handler para el registro de asistentes.
    Implementa control de concurrencia usando TransactWriteItems.
    """
    logger.info(f"Petición de registro: {json.dumps(event)}")
    
    http_method = event.get('httpMethod')
    if http_method != 'POST':
        return build_response(405, {'message': 'Método no permitido'})

    try:
        body = json.loads(event.get('body', '{}'))
    except Exception:
        return build_response(400, {'message': 'JSON body inválido'})

    event_id = body.get('eventId')
    user_id = body.get('userId')
    email = body.get('email')
    name = body.get('name')

    if not all([event_id, user_id, email, name]):
        return build_response(400, {'message': 'Faltan parámetros requeridos (eventId, userId, email, name)'})

    now = datetime.now().isoformat()

    try:
        # Transacción Atómica: Registra al usuario y resta un cupo SOLO si hay cupos disponibles
        # y el evento está en estado PROGRAMADO.
        response = dynamodb.transact_write_items(
            TransactItems=[
                {
                    # 1. Restar cupo al evento (solo si PROGRAMADO y hay cupos)
                    'Update': {
                        'TableName': TABLE_NAME,
                        'Key': {
                            'PK': {'S': f"EVENT#{event_id}"},
                            'SK': {'S': "METADATA"}
                        },
                        'UpdateExpression': 'SET availableCapacity = availableCapacity - :val',
                        'ConditionExpression': 'availableCapacity > :min AND attribute_exists(PK) AND #s = :programado',
                        'ExpressionAttributeNames': {
                            '#s': 'status'
                        },
                        'ExpressionAttributeValues': {
                            ':val': {'N': '1'},
                            ':min': {'N': '0'},
                            ':programado': {'S': 'PROGRAMADO'}
                        }
                    }
                },
                {
                    # 2. Registrar al asistente
                    'Put': {
                        'TableName': TABLE_NAME,
                        'Item': {
                            'PK': {'S': f"EVENT#{event_id}"},
                            'SK': {'S': f"USER#{user_id}"},
                            'name': {'S': name},
                            'email': {'S': email},
                            'registeredAt': {'S': now},
                            # Índices para búsquedas invertidas (ej. ver a qué eventos asiste X usuario)
                            'GSI1PK': {'S': f"USER#{user_id}"},
                            'GSI1SK': {'S': f"EVENT#{event_id}"}
                        },
                        # Evitar registro duplicado del mismo usuario
                        'ConditionExpression': 'attribute_not_exists(PK)'
                    }
                }
            ]
        )
        logger.info(f"Registro exitoso para usuario {user_id} en evento {event_id}")

        # Enviar notificación a SQS para correo de bienvenida
        try:
            sqs = boto3.client('sqs')
            queue_name = f"EventNotificationsQueue-{os.environ.get('ENVIRONMENT', 'lab')}"
            queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
            
            message = {
                'action': 'ASSISTANT_REGISTERED',
                'eventId': event_id,
                'recipientEmail': email,
                'name': name
            }
            sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
        except Exception as sqs_err:
            # Solo loggeamos el error, el registro ya fue exitoso
            logger.error(f"Error enviando mensaje a SQS para bienvenida: {sqs_err}")

        return build_response(201, {'message': 'Registro exitoso'})

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'TransactionCanceledException':
            reasons = e.response.get('CancellationReasons', [])
            # reasons[0] es la Update (cupos/estado), reasons[1] es el Put (duplicado)
            if reasons[0].get('Code') == 'ConditionalCheckFailed':
                # Determinar si falló por estado o por cupos requeriría una lectura adicional;
                # devolvemos el mensaje más informativo cubriendo ambos casos.
                logger.warning(f"Registro fallido: sin cupos o evento no disponible. Evento: {event_id}")
                return build_response(409, {'message': 'No es posible registrarse: el evento no está disponible o ya no hay cupos.'})
            elif len(reasons) > 1 and reasons[1].get('Code') == 'ConditionalCheckFailed':
                logger.warning(f"Registro fallido: usuario ya registrado. Usuario: {user_id}")
                return build_response(409, {'message': 'El usuario ya se encuentra registrado en este evento.'})
            
        logger.error(f"Error en transacción de DynamoDB: {str(e)}")
        return build_response(500, {'message': 'Error interno procesando el registro'})
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return build_response(500, {'message': 'Error interno del servidor'})


def build_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }
