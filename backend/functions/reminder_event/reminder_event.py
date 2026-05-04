import json
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')

def handler(event, context):
    """
    Handler para recordatorios de eventos disparados por EventBridge.
    Envía el mensaje a SQS para que sea procesado por la Lambda de notificaciones (SES).
    """
    logger.info(f"Evento de recordatorio recibido: {json.dumps(event)}")
    
    # Extraer información del evento (inyectada por el Target de EventBridge)
    event_id = event.get('event_id')
    hours_left = event.get('hours_left')
    
    # Obtener URL de la cola
    environment = os.environ.get('ENVIRONMENT', 'lab')
    queue_name = f"EventNotificationsQueue-{environment}"
    
    try:
        queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
        
        # Enviar a SQS
        message = {
            'action': 'SEND_REMINDER',
            'eventId': event_id,
            'hours_left': hours_left,
            'timestamp': os.environ.get('TIMESTAMP', '') # Opcional
        }
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        logger.info(f"Recordatorio de {hours_left}h enviado a SQS para evento {event_id}")
        
        # Eliminar la regla de EventBridge para no dejar basura
        try:
            events_client = boto3.client('events')
            rule_name = f"Reminder{hours_left}h-{event_id}"
            
            # Remover targets primero
            target_response = events_client.list_targets_by_rule(Rule=rule_name)
            target_ids = [t['Id'] for t in target_response.get('Targets', [])]
            if target_ids:
                events_client.remove_targets(Rule=rule_name, Ids=target_ids)
                
            # Borrar la regla
            events_client.delete_rule(Name=rule_name)
            logger.info(f"Regla de EventBridge eliminada: {rule_name}")
        except Exception as rule_err:
            logger.error(f"Error al eliminar la regla {rule_name}: {rule_err}")
            
    except Exception as e:
        logger.error(f"Error en ReminderEvent: {e}")
        return {'statusCode': 500, 'body': str(e)}

    return {'statusCode': 200, 'body': 'Reminder processed'}
