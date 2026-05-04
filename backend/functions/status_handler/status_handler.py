import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.client('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')

def handler(event, context):
    """
    Handler para actualizaciones de estado programadas por EventBridge.
    """
    logger.info(f"Evento recibido de EventBridge: {json.dumps(event)}")
    
    action = event.get('action')
    event_id = event.get('event_id') # Viene de la configuración del target en crud_event.py
    new_status = 'EN_CURSO'

    if not action or action != 'START_EVENT' or not event_id:
        logger.error("Evento inválido o no corresponde a un inicio de evento.")
        return {'statusCode': 400, 'body': 'Evento inválido'}

    try:
        now = datetime.now().isoformat()
        
        # Validar que el evento pase de PROGRAMADO a EN_CURSO
        response = dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={
                'PK': {'S': f"EVENT#{event_id}"},
                'SK': {'S': "METADATA"}
            },
            UpdateExpression="SET #s = :status, updatedAt = :now",
            ExpressionAttributeNames={
                '#s': 'status'
            },
            ExpressionAttributeValues={
                ':status': {'S': new_status},
                ':expected': {'S': 'PROGRAMADO'},
                ':now': {'S': now}
            },
            ConditionExpression="attribute_exists(PK) AND #s = :expected"
        )
        logger.info(f"Estado del evento {event_id} actualizado exitosamente a {new_status}.")
        
        # Eliminar la regla de EventBridge para no dejar basura
        try:
            events_client = boto3.client('events')
            rule_name = f"StatusChange-{event_id}"
            
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

        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'Estado actualizado a {new_status}'})
        }
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.warning(f"Intento fallido de actualizar evento {event_id}. Es posible que no exista o no esté en estado PROGRAMADO.")
            return {'statusCode': 409, 'body': 'El evento no existe o su estado actual no permite la transición a EN_CURSO.'}
        else:
            logger.error(f"Error actualizando DynamoDB: {str(e)}")
            return {'statusCode': 500, 'body': 'Error interno'}
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {'statusCode': 500, 'body': 'Error inesperado'}
