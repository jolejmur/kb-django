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
        self.api_url = "https://graph.facebook.com/v22.0"
        self.channel_layer = get_channel_layer()
        
        # Headers para API requests
        self.headers = {
            'Authorization': f'Bearer {self.config.access_token}',
            'Content-Type': 'application/json'
        }
    
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
    
    def download_media_from_whatsapp(self, media_id, media_type):
        """
        Descarga un archivo multimedia desde WhatsApp API
        """
        import requests
        from django.core.files.base import ContentFile
        from django.utils import timezone
        import os
        
        try:
            # Paso 1: Obtener URL del archivo
            media_url_response = requests.get(
                f"{self.api_url}/{media_id}",
                headers=self.headers
            )
            
            if media_url_response.status_code != 200:
                logger.error(f"Error al obtener URL del media {media_id}: {media_url_response.text}")
                return None
            
            media_data = media_url_response.json()
            file_url = media_data.get('url')
            mime_type = media_data.get('mime_type')
            file_size = media_data.get('file_size')
            
            if not file_url:
                logger.error(f"No se pudo obtener URL para media {media_id}")
                return None
            
            # Paso 2: Descargar el archivo
            file_response = requests.get(
                file_url,
                headers={'Authorization': f'Bearer {self.config.access_token}'}
            )
            
            if file_response.status_code != 200:
                logger.error(f"Error al descargar archivo {file_url}: {file_response.status_code}")
                return None
            
            # Paso 3: Generar nombre de archivo
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            extension = self._get_file_extension_from_mime(mime_type)
            filename = f"{media_type}_{media_id}_{timestamp}{extension}"
            
            # Paso 4: Crear ContentFile para Django
            content_file = ContentFile(file_response.content, name=filename)
            
            return {
                'file': content_file,
                'mime_type': mime_type,
                'size': file_size,
                'filename': filename,
                'url': file_url
            }
            
        except Exception as e:
            logger.error(f"Error descargando media {media_id}: {str(e)}")
            return None
    
    def _get_file_extension_from_mime(self, mime_type):
        """Obtiene la extensión de archivo desde el tipo MIME"""
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png', 
            'image/webp': '.webp',
            'image/gif': '.gif',
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'video/mp4': '.mp4',
            'video/3gpp': '.3gp',
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'text/plain': '.txt'
        }
        return mime_to_ext.get(mime_type, '.dat')
    
    def send_media_message(self, to_number, media_type, media_url, caption=None, filename=None):
        """
        Envía un mensaje multimedia a través de WhatsApp Business API
        """
        import requests
        
        try:
            url = f"{self.api_url}/{self.config.phone_number_id}/messages"
            
            # Construir payload según tipo de media
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": media_type,
                media_type: {
                    "link": media_url
                }
            }
            
            # Agregar caption si se proporciona y el tipo lo soporta
            if caption and media_type in ['image', 'video', 'document']:
                payload[media_type]["caption"] = caption
            
            # Agregar filename para documentos
            if media_type == 'document' and filename:
                payload[media_type]["filename"] = filename
            
            logger.info(f'📤 Enviando payload a WhatsApp API: {payload}')
            response = requests.post(url, headers=self.headers, json=payload)
            response_data = response.json()
            logger.info(f'📥 Respuesta de WhatsApp API: Status {response.status_code}, Data: {response_data}')
            
            if response.status_code == 200:
                message_id = response_data.get('messages', [{}])[0].get('id')
                logger.info(f"✅ Mensaje multimedia enviado exitosamente. ID: {message_id}")
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'response': response_data
                }
            else:
                logger.error(f"❌ Error al enviar mensaje multimedia: Status {response.status_code}")
                logger.error(f"❌ Payload enviado: {payload}")  
                logger.error(f"❌ Respuesta completa: {response_data}")
                
                # Información específica de errores de WhatsApp
                if 'error' in response_data:
                    error_details = response_data['error']
                    logger.error(f"❌ Error code: {error_details.get('code', 'N/A')}")
                    logger.error(f"❌ Error message: {error_details.get('message', 'N/A')}")
                    logger.error(f"❌ Error type: {error_details.get('type', 'N/A')}")
                
                return {
                    'success': False,
                    'error': response_data.get('error', {}).get('message', 'Error desconocido'),
                    'response': response_data
                }
                
        except Exception as e:
            logger.error(f"❌ Excepción al enviar mensaje multimedia: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_media_file(self, to_number, media_type, file_path, caption=None, filename=None):
        """
        Sube un archivo a WhatsApp Media API y luego envía el mensaje
        """
        import requests
        import os
        
        try:
            # Paso 1: Subir archivo a WhatsApp Media API
            media_url = f"{self.api_url}/{self.config.phone_number_id}/media"
            
            # Preparar archivo para upload
            with open(file_path, 'rb') as file_data:
                files = {
                    'file': (filename or os.path.basename(file_path), file_data, 'application/octet-stream')
                }
                
                upload_data = {
                    'messaging_product': 'whatsapp',
                    'type': media_type
                }
                
                # Headers solo con Authorization para upload
                upload_headers = {
                    'Authorization': f'Bearer {self.config.access_token}'
                }
                
                logger.info(f'📤 Subiendo archivo {filename} a WhatsApp Media API...')
                upload_response = requests.post(media_url, headers=upload_headers, data=upload_data, files=files)
                upload_data_response = upload_response.json()
                
                logger.info(f'📥 Respuesta upload: Status {upload_response.status_code}, Data: {upload_data_response}')
                
                if upload_response.status_code != 200:
                    logger.error(f"❌ Error al subir archivo: {upload_data_response}")
                    return {
                        'success': False,
                        'error': upload_data_response.get('error', {}).get('message', 'Error subiendo archivo')
                    }
                
                media_id = upload_data_response.get('id')
                if not media_id:
                    logger.error(f"❌ No se obtuvo media_id del upload")
                    return {
                        'success': False,
                        'error': 'No se pudo obtener ID del archivo subido'
                    }
                
                logger.info(f'✅ Archivo subido exitosamente. Media ID: {media_id}')
            
            # Paso 2: Enviar mensaje usando el media_id
            message_url = f"{self.api_url}/{self.config.phone_number_id}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": media_type,
                media_type: {
                    "id": media_id
                }
            }
            
            # Agregar caption si se proporciona y el tipo lo soporta
            if caption and media_type in ['image', 'video', 'document']:
                payload[media_type]["caption"] = caption
            
            # Agregar filename para documentos
            if media_type == 'document' and filename:
                payload[media_type]["filename"] = filename
            
            logger.info(f'📤 Enviando mensaje con media_id: {payload}')
            response = requests.post(message_url, headers=self.headers, json=payload)
            response_data = response.json()
            logger.info(f'📥 Respuesta mensaje: Status {response.status_code}, Data: {response_data}')
            
            if response.status_code == 200:
                message_id = response_data.get('messages', [{}])[0].get('id')
                logger.info(f"✅ Mensaje multimedia enviado exitosamente. ID: {message_id}")
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'media_id': media_id,
                    'response': response_data
                }
            else:
                logger.error(f"❌ Error al enviar mensaje: {response_data}")
                return {
                    'success': False,
                    'error': response_data.get('error', {}).get('message', 'Error enviando mensaje'),
                    'response': response_data
                }
                
        except Exception as e:
            logger.error(f"❌ Excepción al enviar archivo multimedia: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_media_for_message(self, mensaje, media_data):
        """
        Descarga y procesa un archivo multimedia para un mensaje
        """
        try:
            media_type = media_data.get('type')
            
            # Manejar contactos de manera especial (no requieren descarga)
            if media_type == 'contacts':
                import json
                contact_name = media_data.get('contact_name', 'Sin nombre')
                contact_phone = media_data.get('contact_phone', 'Sin teléfono')
                full_contact_data = media_data.get('full_contact_data', {})
                
                # Guardar información del contacto en los campos del mensaje
                mensaje.archivo_nombre = contact_name
                mensaje.media_url = contact_phone  # Usar media_url para el teléfono
                mensaje.caption = json.dumps(full_contact_data, ensure_ascii=False)  # Datos completos en JSON
                mensaje.archivo_tipo_mime = 'application/vcard'  # Tipo MIME estándar para contactos
                mensaje.save()
                
                logger.info(f"✅ Contacto guardado: {contact_name} ({contact_phone}) para mensaje {mensaje.id}")
                return
            
            # Para otros tipos de media, continuar con la lógica original
            media_id = media_data.get('id')
            if not media_id or not media_type:
                logger.warning(f"Media data incompleto para mensaje {mensaje.id}")
                return
            
            # Descargar archivo desde WhatsApp API
            downloaded_media = self.download_media_from_whatsapp(media_id, media_type)
            
            if downloaded_media:
                # Actualizar campos del mensaje
                mensaje.archivo_url = downloaded_media['url']
                mensaje.archivo_tipo_mime = downloaded_media['mime_type']
                mensaje.archivo_tamaño = downloaded_media['size']
                mensaje.archivo_nombre = downloaded_media['filename']
                
                # Guardar archivo localmente
                mensaje.archivo_local.save(
                    downloaded_media['filename'],
                    downloaded_media['file'],
                    save=False
                )
                
                # Agregar caption si existe
                if media_data.get('caption'):
                    mensaje.caption = media_data['caption']
                elif media_data.get('filename'):
                    mensaje.caption = media_data['filename']
                
                mensaje.save()
                
                logger.info(f"✅ Media descargado exitosamente: {downloaded_media['filename']} para mensaje {mensaje.id}")
            else:
                logger.error(f"❌ No se pudo descargar media {media_id} para mensaje {mensaje.id}")
                
        except Exception as e:
            logger.error(f"❌ Error procesando media para mensaje {mensaje.id}: {str(e)}")
    
    def _process_single_message(self, message, value):
        """
        Procesa un mensaje individual y genera leads automáticamente
        """
        try:
            message_id = message.get('id')
            from_number = message.get('from')
            timestamp = message.get('timestamp')
            message_type = message.get('type')
            
            # Extraer contenido y medios según el tipo de mensaje
            content = ""
            media_data = None
            
            if message_type == 'text':
                content = message.get('text', {}).get('body', '')
            elif message_type == 'image':
                image_data = message.get('image', {})
                content = f"📸 Imagen: {image_data.get('caption', 'Sin caption')}"
                media_data = {
                    'type': 'image',
                    'id': image_data.get('id'),
                    'caption': image_data.get('caption'),
                    'mime_type': image_data.get('mime_type')
                }
            elif message_type == 'audio':
                audio_data = message.get('audio', {})
                content = "🎵 Audio recibido"
                media_data = {
                    'type': 'audio',
                    'id': audio_data.get('id'),
                    'mime_type': audio_data.get('mime_type')
                }
            elif message_type == 'video':
                video_data = message.get('video', {})
                content = f"🎥 Video: {video_data.get('caption', 'Sin caption')}"
                media_data = {
                    'type': 'video',
                    'id': video_data.get('id'),
                    'caption': video_data.get('caption'),
                    'mime_type': video_data.get('mime_type')
                }
            elif message_type == 'document':
                doc_data = message.get('document', {})
                content = f"📄 Documento: {doc_data.get('filename', 'Sin nombre')}"
                media_data = {
                    'type': 'document',
                    'id': doc_data.get('id'),
                    'filename': doc_data.get('filename'),
                    'mime_type': doc_data.get('mime_type')
                }
            elif message_type == 'contacts':
                contacts_data = message.get('contacts', [])
                if contacts_data:
                    contact = contacts_data[0]  # Tomar el primer contacto
                    contact_name = contact.get('name', {}).get('formatted_name', 'Sin nombre')
                    phones = contact.get('phones', [])
                    contact_phone = phones[0].get('phone', 'Sin teléfono') if phones else 'Sin teléfono'
                    content = f"👤 Contacto: {contact_name}"
                    media_data = {
                        'type': 'contacts',
                        'contact_name': contact_name,
                        'contact_phone': contact_phone,
                        'full_contact_data': contact
                    }
                else:
                    content = "👤 Contacto compartido"
                    media_data = {
                        'type': 'contacts',
                        'contact_name': 'Sin nombre',
                        'contact_phone': 'Sin teléfono',
                        'full_contact_data': {}
                    }
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
            
            # NUEVA FUNCIONALIDAD: Crear/actualizar conversación y mensaje
            try:
                self._create_or_update_conversation(from_number, content, message_id, timestamp, message_type, media_data)
            except Exception as conv_error:
                logger.error(f"⚠️ Error al crear conversación: {str(conv_error)}")
            
            # NUEVA FUNCIONALIDAD: Generar lead automáticamente
            try:
                self._create_lead_from_message(from_number, content, message_type)
            except Exception as lead_error:
                logger.error(f"⚠️ Error al crear lead: {str(lead_error)}")
                # No interrumpir el flujo principal si falla la creación del lead
            
            # Log adicional para debugging
            print(f"🔥 MENSAJE RECIBIDO: {from_number} -> {content}")
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje individual: {str(e)}")
    
    def _create_lead_from_message(self, phone_number, content, message_type):
        """
        Crea un lead automáticamente desde un mensaje de WhatsApp
        """
        from .models import Cliente, Lead
        from .lead_distribution_service import LeadDistributionService
        
        # Limpiar número de teléfono (remover prefijo si existe)
        clean_phone = phone_number.replace('+', '').replace(' ', '')
        
        # Crear o obtener cliente
        cliente, created = Cliente.objects.get_or_create(
            numero_whatsapp=clean_phone,
            defaults={
                'nombre': f'Cliente {clean_phone}',
                'apellido': '',
                'origen': 'whatsapp',
                'estado': 'prospecto'  # Inicia como prospecto hasta que compre algo
            }
        )
        
        if created:
            logger.info(f"📋 Cliente nuevo creado: {cliente.nombre_completo} ({clean_phone})")
        else:
            logger.info(f"📋 Cliente existente: {cliente.nombre_completo} ({clean_phone})")
        
        # Verificar si es un mensaje que debe generar lead
        if not self._should_create_lead(content, message_type):
            logger.info(f"📝 Mensaje no genera lead: {content[:50]}...")
            return None
        
        # Verificar si ya existe un lead reciente para este cliente
        from django.utils import timezone
        from datetime import timedelta
        
        recent_lead = Lead.objects.filter(
            cliente=cliente,
            fecha_primera_interaccion__gte=timezone.now() - timedelta(hours=24),
            is_active=True
        ).first()
        
        if recent_lead:
            logger.info(f"⏰ Lead reciente existe para {cliente.nombre_completo}, no crear duplicado")
            return recent_lead
        
        # Crear lead - un prospecto inicial sin inmueble específico
        lead = Lead.objects.create(
            cliente=cliente,
            origen='whatsapp',
            prioridad='media',
            interes_inicial=content[:500] if content else 'Contacto inicial por WhatsApp',
            notas=f'Lead generado automáticamente desde mensaje WhatsApp. Tipo: {message_type}'
        )
        
        logger.info(f"✅ Lead creado: #{lead.id} para {cliente.nombre_completo}")
        
        # Asignar lead automáticamente usando el servicio de distribución
        try:
            distribution_service = LeadDistributionService()
            assignment = distribution_service.assign_lead_to_sales_force(
                lead=lead,
                assigned_by_user=None,  # Sistema automático
                assignment_type='AUTOMATIC'
            )
            
            if assignment:
                logger.info(f"🎯 Lead #{lead.id} asignado a {assignment.organizational_unit.name}")
                print(f"🎯 LEAD ASIGNADO: #{lead.id} → {assignment.organizational_unit.name}")
            else:
                logger.warning(f"⚠️ No se pudo asignar lead #{lead.id}: no hay fuerzas de venta disponibles")
                
        except Exception as assignment_error:
            logger.error(f"❌ Error al asignar lead #{lead.id}: {str(assignment_error)}")
        
        return lead
    
    def _should_create_lead(self, content, message_type):
        """
        Determina si un mensaje debe generar un lead automáticamente
        """
        if not content and message_type != 'text':
            # Mensajes de imagen, audio, video siempre generan lead
            return True
        
        if not content:
            return False
        
        content_lower = content.lower().strip()
        
        # Palabras clave que indican interés en inmuebles
        keywords = [
            'información', 'info', 'precio', 'costa', 'venta', 'comprar',
            'interesado', 'disponible', 'departamento', 'casa', 'terreno',
            'inmueble', 'propiedad', 'inversión', 'financiamiento', 'crédito',
            'visita', 'mostrar', 'ver', 'conocer', 'detalles', 'características',
            'ubicación', 'metros', 'm2', 'habitaciones', 'baños', 'cochera',
            'proyecto', 'planos', 'entrega', 'construcción'
        ]
        
        # Verificar si contiene alguna palabra clave
        for keyword in keywords:
            if keyword in content_lower:
                return True
        
        # Si el mensaje es muy corto (menos de 3 palabras), probablemente no es lead
        if len(content_lower.split()) < 3:
            return False
        
        # Si el mensaje tiene más de 10 caracteres, considerarlo potencial lead
        return len(content_lower) >= 10
    
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
        Valida la ventana de 24 horas de WhatsApp Business
        """
        try:
            # Validar ventana de 24 horas
            if conversation:
                last_incoming_message = conversation.mensajes.filter(
                    direccion='incoming'
                ).order_by('-timestamp_whatsapp').first()
                
                if last_incoming_message:
                    from datetime import timedelta
                    time_limit = timezone.now() - timedelta(hours=24)
                    
                    if last_incoming_message.timestamp_whatsapp < time_limit:
                        return {
                            'success': False,
                            'error': 'VENTANA_24H_EXPIRADA',
                            'error_message': 'La ventana de 24 horas para responder a este cliente ha expirado. Solo puedes responder dentro de las 24 horas desde su último mensaje.',
                            'last_message_time': last_incoming_message.timestamp_whatsapp.isoformat(),
                            'time_limit': time_limit.isoformat()
                        }
                else:
                    # No hay mensajes entrantes del cliente, no se puede enviar mensaje directo
                    return {
                        'success': False,
                        'error': 'SIN_MENSAJE_INICIAL',
                        'error_message': 'Este cliente nunca ha enviado un mensaje. Solo puedes responder después de que el cliente te escriba primero.'
                    }
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
                websocket_data = {
                    'id': debug_message.id,
                    'tipo': 'outgoing',
                    'numero_telefono': numero_telefono,
                    'contenido': contenido,
                    'estado': 'enviado',
                    'created_at': debug_message.created_at.isoformat(),
                    'message_id': message_id
                }
                
                # Agregar información de conversación si está disponible
                if conversation:
                    websocket_data['conversacion_id'] = conversation.id
                    websocket_data['cliente_nombre'] = conversation.cliente.nombre_completo
                
                self._notify_websocket(websocket_data)
                
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
    
    def _create_or_update_conversation(self, from_number, content, message_id, timestamp, message_type, media_data=None):
        """
        Crea o actualiza una conversación y mensaje en la base de datos
        """
        from .models import Cliente, Conversacion, Mensaje
        from django.utils import timezone
        from datetime import datetime
        
        # Limpiar número de teléfono
        clean_phone = from_number.replace('+', '').replace(' ', '')
        
        # Buscar o crear cliente
        cliente, created = Cliente.objects.get_or_create(
            numero_whatsapp=clean_phone,
            defaults={
                'nombre': f'Cliente {clean_phone}',
                'apellido': '',
                'origen': 'whatsapp',
                'estado': 'prospecto'
            }
        )
        
        # Buscar o crear conversación
        conversacion, conv_created = Conversacion.objects.get_or_create(
            numero_whatsapp=clean_phone,
            defaults={
                'cliente': cliente,
                'estado': 'abierta',
                'is_active': True,
                'ultimo_mensaje_at': timezone.now(),
                'mensajes_no_leidos': 0
            }
        )
        
        # Convertir timestamp de WhatsApp a datetime
        message_datetime = timezone.now()
        if timestamp:
            try:
                message_datetime = datetime.fromtimestamp(int(timestamp), tz=timezone.get_current_timezone())
            except (ValueError, TypeError):
                message_datetime = timezone.now()
        
        # Crear mensaje
        mensaje = Mensaje.objects.create(
            conversacion=conversacion,
            whatsapp_message_id=message_id or f'msg_{int(timezone.now().timestamp())}',
            tipo=message_type or 'text',
            direccion='incoming',
            contenido=content,
            estado='entregado',
            timestamp_whatsapp=message_datetime
        )
        
        # Procesar medios si hay datos
        if media_data and media_data.get('id'):
            self._process_media_for_message(mensaje, media_data)
        
        # Actualizar conversación
        conversacion.ultimo_mensaje_at = message_datetime
        conversacion.mensajes_no_leidos += 1
        conversacion.save()
        
        if conv_created:
            logger.info(f"💬 Nueva conversación creada: {clean_phone}")
        else:
            logger.info(f"💬 Conversación actualizada: {clean_phone}")
        
        logger.info(f"📨 Mensaje guardado: ID {mensaje.id} en conversación {conversacion.id}")
        
        # Notificar WebSocket sobre el nuevo mensaje entrante
        self._notify_websocket({
            'id': mensaje.id,
            'tipo': 'incoming',
            'numero_telefono': clean_phone,
            'contenido': content,
            'conversacion_id': conversacion.id,
            'cliente_nombre': cliente.nombre_completo,
            'estado': 'entregado',
            'created_at': mensaje.timestamp_whatsapp.isoformat(),
            'message_type': message_type
        })
        
        return conversacion, mensaje