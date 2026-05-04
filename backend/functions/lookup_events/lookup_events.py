import json
import os
import logging
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 > 0 else int(obj)
        return super(DecimalEncoder, self).default(obj)


def handler(event, context):
    """
    Lambda para consulta de eventos (Read-only).
    Maneja GET /events y GET /events/{id}.
    GET /events              → eventos con status PROGRAMADO (vista asistente)
    GET /events?includeAll=true → todos los eventos (vista organizador)
    """
    logger.info(f"Lookup event: {json.dumps(event)}")

    path_parameters = event.get('pathParameters') or {}
    query_params = event.get('queryStringParameters') or {}
    event_id = path_parameters.get('id')
    include_all = query_params.get('includeAll', 'false').lower() == 'true'

    table = dynamodb.Table(TABLE_NAME)

    try:
        if event_id:
            return get_event_details(table, event_id)
        else:
            return list_events(table, include_all)

    except Exception as e:
        logger.error(f"Error en lookup: {str(e)}")
        return build_response(500, {'message': 'Error consultando eventos'})


def get_event_details(table, event_id):
    """Obtiene los detalles de un evento específico."""
    response = table.get_item(
        Key={
            'PK': f"EVENT#{event_id}",
            'SK': "METADATA"
        }
    )
    item = response.get('Item')
    if not item:
        return build_response(404, {'message': 'Evento no encontrado'})
    return build_response(200, item)


def list_events(table, include_all: bool):
    """
    Lista eventos usando EventsByStatusGSI.
    - include_all=False: solo PROGRAMADO (vista pública para asistentes)
    - include_all=True:  todos los estados (vista del organizador)
    """
    if include_all:
        # Scan con filtro SK=METADATA para obtener todos los eventos sin importar estado
        response = table.scan(FilterExpression=Attr('SK').eq('METADATA'))
        items = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=Attr('SK').eq('METADATA'),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
    else:
        # Consulta eficiente usando GSI EventsByStatusGSI (solo eventos PROGRAMADO)
        response = table.query(
            IndexName='EventsByStatusGSI',
            KeyConditionExpression=Key('status').eq('PROGRAMADO')
        )
        items = response.get('Items', [])
        while 'LastEvaluatedKey' in response:
            response = table.query(
                IndexName='EventsByStatusGSI',
                KeyConditionExpression=Key('status').eq('PROGRAMADO'),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

    logger.info(f"Eventos encontrados: {len(items)} (includeAll={include_all})")
    return build_response(200, items)


def build_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }