import json
import os
import logging
import boto3
import uuid
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


# NFR: Configuración de Logging centralizado y niveles adecuados
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')
sqs = boto3.client('sqs')

TABLE_NAME = os.environ.get('TABLE_NAME')
# Extraer el environment de alguna variable o usar por defecto 'lab'
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'lab')

def get_queue_url():
    """Obtiene la URL de la cola SQS de notificaciones."""
    queue_name = f"EventNotificationsQueue-{ENVIRONMENT}"
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except ClientError as e:
        logger.error(f"Error getting queue URL: {e}")
        return None


def manage_eventbridge_rule(event_id, action, start_date=None):
    """Crea o elimina reglas de EventBridge para recordatorios y cambio de estado."""
    try:
        # Definir nombres de las reglas basados en el ID del evento
        rules = {
            'status': f"StatusChange-{event_id}",
            'rem24': f"Reminder24h-{event_id}",
            'rem12': f"Reminder12h-{event_id}"
        }

        if action == 'DELETE':
            for rule_name in rules.values():
                logger.info(f"Eliminando regla y targets: {rule_name}")
                try:
                    # Primero remover targets asociados
                    response = eventbridge.list_targets_by_rule(Rule=rule_name)
                    target_ids = [t['Id'] for t in response.get('Targets', [])]
                    if target_ids:
                        eventbridge.remove_targets(Rule=rule_name, Ids=target_ids)
                    
                    # Eliminar la regla
                    eventbridge.delete_rule(Name=rule_name)
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceNotFoundException':
                        logger.error(f"Error al eliminar regla {rule_name}: {e}")
            return

        if action == 'CREATE' and start_date:
            # Parsear fecha de inicio (asumiendo ISO format UTC)
            dt_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            # Definir tareas (Status Handler y Reminders)
            tasks = [
                {
                    'name': rules['status'], 
                    'time': dt_start, 
                    'arn': os.environ.get('STATUS_HANDLER_LAMBDA_ARN'), 
                    'input': {'event_id': event_id, 'action': 'START_EVENT'}
                },
                {
                    'name': rules['rem24'], 
                    'time': dt_start - timedelta(hours=24), 
                    'arn': os.environ.get('REMINDER_LAMBDA_ARN'), 
                    'input': {'event_id': event_id, 'hours_left': 24}
                },
                {
                    'name': rules['rem12'], 
                    'time': dt_start - timedelta(hours=12), 
                    'arn': os.environ.get('REMINDER_LAMBDA_ARN'), 
                    'input': {'event_id': event_id, 'hours_left': 12}
                },
            ]

            now = datetime.now(dt_start.tzinfo)

            for task in tasks:
                # Solo crear reglas para tiempos futuros
                if task['time'] > now and task['arn']:
                    # Formato Cron EventBridge: cron(Minutes Hours Day-of-month Month Day-of-week Year)
                    cron = f"cron({task['time'].minute} {task['time'].hour} {task['time'].day} {task['time'].month} ? {task['time'].year})"
                    
                    logger.info(f"Programando regla {task['name']} con cron {cron}")
                    
                    eventbridge.put_rule(
                        Name=task['name'],
                        ScheduleExpression=cron,
                        State='ENABLED',
                        Description=f"Automatización para el evento {event_id}"
                    )

                    eventbridge.put_targets(
                        Rule=task['name'],
                        Targets=[{
                            'Id': f"Target-{task['name']}",
                            'Arn': task['arn'],
                            'Input': json.dumps(task['input'])
                        }]
                    )
                elif not task['arn']:
                    logger.warning(f"No se pudo crear regla {task['name']}: ARN no configurado en variables de entorno")
                else:
                    logger.info(f"Omitiendo regla {task['name']}: El tiempo ya pasó o es muy próximo.")

    except Exception as e:
        logger.error(f"Excepción en manage_eventbridge_rule: {str(e)}")


def send_sqs_notification(message, recipient_email):
    """Envía un mensaje a SQS cuando hay cambios importantes o se elimina un evento."""
    queue_url = get_queue_url()
    if queue_url:
        try:
            # Incluimos el destinatario en el mensaje para la Lambda de notificaciones
            message['recipientEmail'] = recipient_email
            
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            logger.info(f"Notificación SQS enviada para acción: {message.get('action')}")
        except Exception as e:
            logger.error(f"Error enviando a SQS: {e}")

def handler(event, context):
    """
    Lambda CRUD Handler (Crear, Editar, Eliminar).
    Maneja POST /events, PUT /events/{id} y DELETE /events/{id}.
    """
    logger.info(f"CRUD Event request: {json.dumps(event)}")
    
    http_method = event.get('httpMethod')
    path_parameters = event.get('pathParameters') or {}
    event_id = path_parameters.get('id')
    
    body = {}
    if event.get('body'):
        try:
            body = json.loads(event.get('body'))
        except Exception:
            return build_response(400, {'message': 'JSON body inválido'})

    table = dynamodb.Table(TABLE_NAME)

    resource = event.get('resource', '')

    try:
        if '/notifications' in resource and http_method == 'POST':
            return send_mass_notification(table, event_id, body)
        elif http_method == 'POST':
            return create_event(table, body)
        elif http_method == 'PUT':
            return update_event(table, event_id, body)
        elif http_method == 'DELETE':
            return delete_event(table, event_id)
        else:
            return build_response(405, {'message': f'Método {http_method} no soportado en esta función'})
            
    except ClientError as e:
        logger.error(f"Error de DynamoDB: {e}")
        return build_response(500, {'message': 'Error de base de datos'})
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return build_response(500, {'message': 'Error interno del servidor'})

def create_event(table, body):
    # Validaciones básicas
    required_fields = ['name', 'startDate', 'organizerId', 'capacity']
    for field in required_fields:
        if field not in body:
            return build_response(400, {'message': f'Campo {field} es requerido'})

    try:
        capacity = int(body['capacity'])
        if capacity <= 0:
            return build_response(400, {'message': 'Capacity debe ser mayor a 0'})
    except ValueError:
        return build_response(400, {'message': 'Capacity debe ser un número entero'})

    event_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    item = {
        'PK': f"EVENT#{event_id}",
        'SK': "METADATA",
        'id': event_id,
        'name': body['name'],
        'startDate': body['startDate'],
        'endDate': body.get('endDate', ''),
        'location': body.get('location', ''),
        'organizerId': body['organizerId'],
        'organizerEmail': body.get('organizerEmail', ''),
        'status': 'PROGRAMADO',
        'capacity': capacity,
        'availableCapacity': capacity,
        'createdAt': now,
        'updatedAt': now,
        'description': body.get('description', ''),
        # GSI Attributes
        'GSI1PK': f"ORG#{body['organizerId']}",
        'GSI1SK': f"EVENT#{event_id}"
    }
    
    table.put_item(Item=item)
    
    # Arquitectura: Integración con EventBridge
    manage_eventbridge_rule(event_id, 'CREATE', body['startDate'])
    
    return build_response(201, {'message': 'Evento creado', 'event': item})

def update_event(table, event_id, body):
    if not event_id:
        return build_response(400, {'message': 'El ID del evento es requerido'})

    now = datetime.now().isoformat()
    
    update_expr = "SET updatedAt = :u"
    expr_names = {}
    expr_values = {':u': now}

    if 'name' in body:
        update_expr += ", #name = :n"
        expr_names['#name'] = 'name'
        expr_values[':n'] = body['name']
    
    if 'description' in body:
        update_expr += ", description = :d"
        expr_values[':d'] = body['description']

    if 'startDate' in body:
        update_expr += ", startDate = :sd"
        expr_values[':sd'] = body['startDate']

    if 'location' in body:
        update_expr += ", #l = :l"
        expr_names['#l'] = 'location'
        expr_values[':l'] = body['location']

    if 'capacity' in body:
        update_expr += ", #cap = :c"
        expr_names['#cap'] = 'capacity'
        expr_values[':c'] = body['capacity']

    if 'status' in body:
        update_expr += ", #s = :s"
        expr_names['#s'] = 'status'
        expr_values[':s'] = body['status']

    if not expr_names and 'description' not in body and 'startDate' not in body and 'capacity' not in body:
        return build_response(400, {'message': 'No hay campos válidos para actualizar'})

    kwargs = {
        'Key': {
            'PK': f"EVENT#{event_id}",
            'SK': "METADATA"
        },
        'UpdateExpression': update_expr,
        'ExpressionAttributeValues': expr_values,
        'ConditionExpression': "attribute_exists(PK)"
    }
    
    # Validaciones estrictas de transición de estado
    if body.get('status') == 'FINALIZADO':
        # Solo se puede finalizar si está EN_CURSO
        kwargs['ConditionExpression'] += " AND #s = :expected_status"
        kwargs['ExpressionAttributeValues'][':expected_status'] = 'EN_CURSO'
    elif body.get('status') == 'CANCELADO':
        # No se puede cancelar si ya está CANCELADO o FINALIZADO
        kwargs['ConditionExpression'] += " AND #s <> :already_cancelled AND #s <> :finalizado"
        kwargs['ExpressionAttributeValues'][':already_cancelled'] = 'CANCELADO'
        kwargs['ExpressionAttributeValues'][':finalizado'] = 'FINALIZADO'

    if expr_names:
        kwargs['ExpressionAttributeNames'] = expr_names

    try:
        table.update_item(**kwargs)

        # Si cambió la fecha de inicio, reprogramar las reglas de EventBridge
        if 'startDate' in body:
            manage_eventbridge_rule(event_id, 'DELETE')
            manage_eventbridge_rule(event_id, 'CREATE', body['startDate'])

        # Determinar el tipo de acción a notificar
        if body.get('status') == 'FINALIZADO':
            action = 'EVENT_COMPLETED'
        elif body.get('status') == 'CANCELADO':
            action = 'EVENT_CANCELLED'
        else:
            action = 'EVENT_UPDATED'

        # Notificar cambio vía SQS
        send_sqs_notification({
            'action': action,
            'eventId': event_id,
            'timestamp': now
        }, body.get('organizerEmail'))
        
        return build_response(200, {'message': 'Evento actualizado exitosamente'})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            if body.get('status') == 'FINALIZADO':
                return build_response(400, {'message': 'No se puede finalizar el evento: debe estar EN_CURSO.'})
            if body.get('status') == 'CANCELADO':
                return build_response(400, {'message': 'No se puede cancelar el evento: ya está CANCELADO o FINALIZADO.'})
            return build_response(404, {'message': 'Evento no encontrado'})
        raise e

def delete_event(table, event_id):
    if not event_id:
        return build_response(400, {'message': 'El ID del evento es requerido'})

    # 1. Obtener a todos los asistentes para guardar sus correos y poder borrarlos
    attendee_emails = []
    try:
        response = table.query(
            KeyConditionExpression=Key('PK').eq(f"EVENT#{event_id}") & Key('SK').begins_with("USER#")
        )
        for item in response.get('Items', []):
            if 'email' in item:
                attendee_emails.append(item['email'])
            # 2. Eliminar al asistente de la base de datos
            table.delete_item(
                Key={
                    'PK': f"EVENT#{event_id}",
                    'SK': item['SK']
                }
            )
    except Exception as e:
        logger.error(f"Error procesando asistentes durante la eliminación: {e}")

    # 3. Eliminar el evento en sí
    table.delete_item(
        Key={
            'PK': f"EVENT#{event_id}",
            'SK': "METADATA"
        }
    )
    
    # 4. Arquitectura: Limpiar reglas en EventBridge
    manage_eventbridge_rule(event_id, 'DELETE')
    
    # 5. Notificar eliminación vía SQS pasando la lista de correos rescatada
    send_sqs_notification({
        'action': 'EVENT_DELETED',
        'eventId': event_id,
        'attendeeEmails': attendee_emails
    }, None)
    
    return build_response(200, {'message': 'Evento y asistentes eliminados'})

def send_mass_notification(table, event_id, body):
    if not event_id:
        return build_response(400, {'message': 'El ID del evento es requerido'})

    subject = body.get('subject', '').strip()
    message_body = body.get('message', '').strip()

    if not subject or not message_body:
        return build_response(400, {'message': 'Los campos subject y message son requeridos'})

    # Verificar que el evento existe antes de encolar
    item = table.get_item(Key={'PK': f"EVENT#{event_id}", 'SK': 'METADATA'}).get('Item')
    if not item:
        return build_response(404, {'message': 'Evento no encontrado'})

    send_sqs_notification({
        'action': 'MASS_NOTIFICATION',
        'eventId': event_id,
        'subject': subject,
        'messageBody': message_body,
        'timestamp': datetime.now().isoformat()
    }, None)

    return build_response(202, {'message': 'Notificación masiva encolada exitosamente'})


def build_response(status_code, body):
    """Construye la respuesta HTTP estándar con cabeceras CORS de Seguridad (NFR)."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*', # NFR: CORS
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': json.dumps(body)
    }

