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

def get_attendee_emails(event_id):
    """Consulta en DynamoDB todos los asistentes registrados para un evento."""
    table = dynamodb.Table(TABLE_NAME)
    emails = []
    try:
        # Según el diseño Single-Table: PK=EVENT#{id}, SK=USER#{userId}
        response = table.query(
            KeyConditionExpression=Key('PK').eq(f"EVENT#{event_id}") & Key('SK').begins_with("USER#")
        )
        for item in response.get('Items', []):
            if 'email' in item:
                emails.append(item['email'])

        # Manejar paginación si hay muchos asistentes
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

def send_email(to_addresses, subject, body):
    """Envía el correo usando Amazon SES."""
    if not to_addresses:
        logger.info("No hay destinatarios para enviar el correo.")
        return

    try:
        response = ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={
                'ToAddresses': to_addresses if isinstance(to_addresses, list) else [to_addresses]
            },
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': body},
                    'Text': {'Data': body}
                }
            }
        )
        logger.info(f"Correo enviado exitosamente. MessageId: {response['MessageId']}")
    except ClientError as e:
        logger.error(f"Error de SES al enviar correo: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Error inesperado al enviar correo: {str(e)}")

def handler(event, context):
    """
    Handler disparado por SQS para enviar notificaciones.
    Soporta notificaciones directas o broadcast a asistentes de un evento.
    """
    logger.info(f"Procesando batch de {len(event['Records'])} mensajes SQS.")
    
    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            action = message.get('action')
            event_id = message.get('eventId')
            recipient_email = message.get('recipientEmail')
            
            logger.info(f"Acción: {action}, Evento: {event_id}")

            # 1. Registro de asistente (Bienvenida)
            if action == 'ASSISTANT_REGISTERED':
                subject = f"¡Bienvenido al evento!"
                body_content = f"<h1>Registro Exitoso</h1><p>Hola {message.get('name', '')}, te has registrado exitosamente en el evento con ID {event_id}.</p>"
                send_email(recipient_email, subject, body_content)
                
            # 2. Evento Cancelado (Notificación a asistentes)
            elif action == 'EVENT_CANCELLED':
                subject = "Evento cancelado"
                body_content = f"<h1>Evento Cancelado</h1><p>Lamentamos informarte que el evento con ID <b>{event_id}</b> ha sido cancelado. Si tienes dudas, contacta al organizador.</p>"
                recipients = get_attendee_emails(event_id)
                if recipient_email and recipient_email not in recipients:
                    recipients.append(recipient_email)
                if recipients:
                    logger.info(f"Enviando cancelación a {len(recipients)} destinatarios.")
                    send_email(recipients, subject, body_content)
                else:
                    logger.info(f"No se encontraron destinatarios para el evento cancelado {event_id}.")

            # 3. Evento Finalizado (Agradecimiento)
            elif action == 'EVENT_COMPLETED':
                subject = f"¡Gracias por asistir!"
                body_content = f"<h1>Evento Finalizado</h1><p>El evento con ID {event_id} ha finalizado. ¡Esperamos que lo hayas disfrutado! Gracias por acompañarnos.</p>"
                
                recipients = get_attendee_emails(event_id)
                if recipients:
                    logger.info(f"Enviando agradecimiento a {len(recipients)} asistentes.")
                    send_email(recipients, subject, body_content)
                else:
                    logger.info(f"No se encontraron asistentes para el evento finalizado {event_id}.")
            
            # 3. Recordatorio automático (disparado por EventBridge → ReminderEvent → SQS)
            elif action == 'SEND_REMINDER' and event_id:
                hours_left = message.get('hours_left', '?')
                subject = f"Recordatorio: tu evento comienza en {hours_left} horas"
                body_content = (
                    f"<h1>¡Tu evento está próximo!</h1>"
                    f"<p>Te recordamos que el evento con ID <b>{event_id}</b> "
                    f"comenzará en aproximadamente <b>{hours_left} horas</b>.</p>"
                    f"<p>¡Prepárate y no faltes!</p>"
                )
                recipients = get_attendee_emails(event_id)
                if recipients:
                    logger.info(f"Enviando recordatorio de {hours_left}h a {len(recipients)} asistentes.")
                    send_email(recipients, subject, body_content)
                else:
                    logger.info(f"No se encontraron asistentes para el recordatorio del evento {event_id}.")

            # 4. Notificación masiva personalizada enviada por el organizador
            elif action == 'MASS_NOTIFICATION' and event_id:
                custom_subject = message.get('subject', 'Mensaje del organizador')
                custom_body_text = message.get('messageBody', '')
                body_content = f"<h1>{custom_subject}</h1><p>{custom_body_text}</p>"
                recipients = get_attendee_emails(event_id)
                if recipients:
                    logger.info(f"Enviando notificación masiva a {len(recipients)} asistentes del evento {event_id}.")
                    send_email(recipients, custom_subject, body_content)
                else:
                    logger.info(f"No se encontraron asistentes para la notificación masiva del evento {event_id}.")

            # 5. Actualización o Eliminación (Broadcast a asistentes + organizador)
            elif event_id and action in ['EVENT_UPDATED', 'EVENT_DELETED']:
                subject = f"Actualización de evento"
                body_content = (
                    f"<h1>Actualización de Evento</h1>"
                    f"<p>Se ha realizado una actualización en el evento con ID <b>{event_id}</b>. "
                    f"Acción: <b>{action}</b>.</p>"
                )

                # Obtener asistentes (si vienen en el mensaje usamos esos, si no, consultamos BD)
                recipients = message.get('attendeeEmails')
                if recipients is None:
                    recipients = get_attendee_emails(event_id)

                # Añadir al organizador/administrador (viene en recipient_email desde crud_event.py)
                if recipient_email and recipient_email not in recipients:
                    recipients.append(recipient_email)

                if recipients:
                    logger.info(f"Enviando broadcast a {len(recipients)} destinatarios.")
                    send_email(recipients, subject, body_content)
                else:
                    logger.info(f"No se encontraron destinatarios para el evento {event_id}.")
            
            else:
                logger.warning(f"Mensaje SQS no reconocido o incompleto: {message}")

        except Exception as e:
            logger.error(f"Error procesando mensaje SQS: {e}")
            # Al lanzar excepción, SQS reintentará el mensaje (según VisibilityTimeout/RedrivePolicy)
            raise e

    return {'status': 'done'}

