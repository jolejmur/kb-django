# apps/whatsapp_business/services.py
import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import WhatsAppConfig, WebhookDebugMessage

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Servicio para manejar el envío de mensajes de WhatsApp
    """
    
    def __init__(self):
        self.config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not self.config:
            raise ValueError("No hay configuración activa de WhatsApp")
        self.channel_layer = get_channel_layer()
    
    def _notify_websocket(self, message_data):
        """Notify WebSocket clients of new message"""
        if self.channel_layer:
            async_to_sync(self.channel_layer.group_send)(
                'whatsapp_messages',
                {
                    'type': 'whatsapp_message',
                    'message': message_data
                }
            )
    
    def send_template_message(self, to_number, template_name='hello_world', language_code='en_US', parameters=None):
        """
        Envía un mensaje de template de WhatsApp
        """
        try:
            url = f"https://graph.facebook.com/v22.0/{self.config.phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {self.config.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language_code
                    }
                }
            }
            
            # Agregar parámetros si existen
            if parameters:
                payload["template"]["components"] = parameters
            
            logger.info(f"Enviando mensaje a {to_number}: {payload}")
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            # Guardar mensaje de debug
            debug_message = WebhookDebugMessage.objects.create(
                tipo='test_message',
                numero_telefono=to_number,
                contenido=f"Template: {template_name} ({language_code})",
                raw_data=payload,
                respuesta_api=response_data,
                estado='sent' if response.status_code == 200 else 'error',
                config_utilizada=self.config
            )
            
            if response.status_code == 200:
                logger.info(f"Mensaje enviado exitosamente: {response_data}")
                return {
                    'success': True,
                    'message_id': response_data.get('messages', [{}])[0].get('id'),
                    'response': response_data
                }
            else:
                logger.error(f"Error al enviar mensaje: {response_data}")
                return {
                    'success': False,
                    'error': response_data.get('error', {}).get('message', 'Error desconocido'),
                    'response': response_data
                }
                
        except Exception as e:
            logger.error(f"Excepción al enviar mensaje: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'response': None
            }
    
    def send_text_message(self, to_number, text):
        """
        Envía un mensaje de texto simple
        """
        try:
            url = f"https://graph.facebook.com/v22.0/{self.config.phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {self.config.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {
                    "body": text
                }
            }
            
            logger.info(f"Enviando mensaje de texto a {to_number}: {text}")
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            # Guardar mensaje de debug
            debug_message = WebhookDebugMessage.objects.create(
                tipo='outgoing',
                numero_telefono=to_number,
                contenido=text,
                raw_data=payload,
                respuesta_api=response_data,
                estado='sent' if response.status_code == 200 else 'error',
                config_utilizada=self.config
            )
            
            # Notificar WebSocket
            self._notify_websocket({
                'id': debug_message.id,
                'tipo': 'outgoing',
                'numero_telefono': to_number,
                'contenido': text,
                'estado': 'sent' if response.status_code == 200 else 'error',
                'created_at': debug_message.created_at.isoformat(),
                'action': 'new_message'
            })
            
            if response.status_code == 200:
                logger.info(f"Mensaje de texto enviado exitosamente: {response_data}")
                return {
                    'success': True,
                    'message_id': response_data.get('messages', [{}])[0].get('id'),
                    'response': response_data
                }
            else:
                logger.error(f"Error al enviar mensaje de texto: {response_data}")
                return {
                    'success': False,
                    'error': response_data.get('error', {}).get('message', 'Error desconocido'),
                    'response': response_data
                }
                
        except Exception as e:
            logger.error(f"Excepción al enviar mensaje de texto: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'response': None
            }
    
    def process_webhook_message(self, webhook_data):
        """
        Procesa un mensaje recibido del webhook
        """
        try:
            logger.info(f"🔄 Procesando webhook: {webhook_data}")
            
            # Log interno sin guardar en BD
            logger.info(f"🔄 Webhook recibido: {len(webhook_data.get('entry', []))} entradas")
            
            # Procesar cada entrada en el webhook
            for entry in webhook_data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        
                        # Procesar mensajes
                        for message in value.get('messages', []):
                            self._process_single_message(message, value)
                        
                        # Procesar estados de mensajes
                        for status in value.get('statuses', []):
                            self._process_message_status(status, value)
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"❌ Error al procesar webhook: {str(e)}")
            
            # Log error interno sin guardar en BD
            logger.error(f"❌ Error procesando webhook: {str(e)}")
            
            return {'success': False, 'error': str(e)}
    
    def _process_single_message(self, message, value):
        """
        Procesa un mensaje individual
        """
        try:
            message_id = message.get('id')
            from_number = message.get('from')
            timestamp = message.get('timestamp')
            message_type = message.get('type')
            
            # Extraer contenido según el tipo de mensaje
            content = ""
            if message_type == 'text':
                content = message.get('text', {}).get('body', '')
            elif message_type == 'image':
                content = f"Imagen recibida: {message.get('image', {}).get('caption', 'Sin caption')}"
            elif message_type == 'audio':
                content = "Audio recibido"
            elif message_type == 'video':
                content = f"Video recibido: {message.get('video', {}).get('caption', 'Sin caption')}"
            elif message_type == 'document':
                content = f"Documento recibido: {message.get('document', {}).get('filename', 'Sin nombre')}"
            else:
                content = f"Mensaje de tipo {message_type} recibido"
            
            # Guardar mensaje de debug
            debug_message = WebhookDebugMessage.objects.create(
                tipo='incoming',
                numero_telefono=from_number,
                contenido=content,
                raw_data=message,
                estado='received',
                config_utilizada=self.config
            )
            
            # Notificar WebSocket
            self._notify_websocket({
                'id': debug_message.id,
                'tipo': 'incoming',
                'numero_telefono': from_number,
                'contenido': content,
                'estado': 'received',
                'created_at': debug_message.created_at.isoformat(),
                'action': 'new_message'
            })
            
            logger.info(f"📨 Mensaje procesado: {message_id} de {from_number}: {content}")
            
            # Log adicional para debugging
            print(f"🔥 MENSAJE RECIBIDO: {from_number} -> {content}")
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje individual: {str(e)}")
    
    def _process_message_status(self, status, value):
        """
        Procesa el estado de un mensaje
        """
        try:
            message_id = status.get('id')
            recipient_id = status.get('recipient_id')
            status_type = status.get('status')
            timestamp = status.get('timestamp')
            
            # Log estado interno sin guardar en BD
            logger.info(f"📋 Estado del mensaje {message_id}: {status_type}")
            
            logger.info(f"Estado de mensaje procesado: {message_id} -> {status_type}")
            
        except Exception as e:
            logger.error(f"Error al procesar estado de mensaje: {str(e)}")
    
    def get_debug_messages(self, limit=4):
        """
        Obtiene los últimos mensajes de debug
        """
        return WebhookDebugMessage.objects.filter(
            config_utilizada=self.config
        ).order_by('-created_at')[:limit]
    
    def send_message(self, numero_telefono, contenido, conversation=None, usuario_envio=None):
        """
        Envía un mensaje de texto a través de WhatsApp Business API
        """
        try:
            # Preparar datos del mensaje
            data = {
                'messaging_product': 'whatsapp',
                'to': numero_telefono,
                'type': 'text',
                'text': {
                    'body': contenido
                }
            }
            
            headers = {
                'Authorization': f'Bearer {self.config.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Enviar mensaje a Meta API
            response = requests.post(
                f'{self.api_url}/{self.config.phone_number_id}/messages',
                json=data,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id')
                
                # Crear o actualizar conversación si se proporciona
                if conversation:
                    # Crear registro del mensaje en la BD
                    from .models import Mensaje
                    mensaje = Mensaje.objects.create(
                        conversacion=conversation,
                        whatsapp_message_id=message_id,
                        contenido=contenido,
                        tipo='text',
                        direccion='outgoing',
                        estado='enviado',
                        enviado_por=usuario_envio,
                        timestamp_whatsapp=timezone.now()
                    )
                    
                    # Actualizar conversación
                    conversation.ultimo_mensaje_at = mensaje.created_at
                    conversation.save()
                
                # Guardar mensaje de debug
                debug_message = WebhookDebugMessage.objects.create(
                    tipo='outgoing',
                    numero_telefono=numero_telefono,
                    contenido=contenido,
                    raw_data=response_data,
                    estado='enviado',
                    config_utilizada=self.config
                )
                
                # Notificar WebSocket
                self._notify_websocket({
                    'id': debug_message.id,
                    'tipo': 'outgoing',
                    'numero_telefono': numero_telefono,
                    'contenido': contenido,
                    'estado': 'enviado',
                    'created_at': debug_message.created_at.isoformat(),
                })
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'response': response_data
                }
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                logger.error(f"❌ Error enviando mensaje: {error_msg}")
                
                # Guardar mensaje de debug con error
                WebhookDebugMessage.objects.create(
                    tipo='outgoing',
                    numero_telefono=numero_telefono,
                    contenido=contenido,
                    raw_data={'error': error_msg},
                    estado='error',
                    config_utilizada=self.config
                )
                
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {str(e)}")
            
            # Guardar mensaje de debug con error
            WebhookDebugMessage.objects.create(
                tipo='outgoing',
                numero_telefono=numero_telefono,
                contenido=contenido,
                raw_data={'error': str(e)},
                estado='error',
                config_utilizada=self.config
            )
            
            return {
                'success': False,
                'error': str(e)
            }