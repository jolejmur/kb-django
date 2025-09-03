# apps/communications/services/message_service.py
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from ..models import Mensaje, Conversacion, WhatsAppConfig, Cliente, WebhookDebugMessage
import requests
import logging
import os
import tempfile
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageService:
    """
    Servicio para manejar la lógica de negocio de mensajes
    """
    
    @staticmethod
    def send_text_message(conversation, content, user):
        """
        Envía un mensaje de texto
        """
        try:
            config = WhatsAppConfig.objects.filter(is_active=True).first()
            if not config:
                return False, "No hay configuración activa de WhatsApp"
            
            # Enviar mensaje usando requests directamente (simplificado)
            api_url = "https://graph.facebook.com/v22.0"
            headers = {
                'Authorization': f'Bearer {config.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'to': conversation.numero_whatsapp,
                'type': 'text',
                'text': {
                    'body': content
                }
            }
            
            import requests
            response = requests.post(
                f'{api_url}/{config.phone_number_id}/messages',
                json=data,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                message_id = response_data.get('messages', [{}])[0].get('id')
                
                # Crear mensaje en BD
                mensaje = Mensaje.objects.create(
                    conversacion=conversation,
                    whatsapp_message_id=message_id,
                    contenido=content,
                    tipo='text',
                    direccion='outgoing',
                    estado='sent',
                    enviado_por=user,
                    timestamp_whatsapp=timezone.now()
                )
                
                # Crear WebhookDebugMessage para mostrar en el historial de configuración
                try:
                    WebhookDebugMessage.objects.create(
                        tipo='outgoing',
                        numero_telefono=conversation.numero_whatsapp,
                        contenido=content,
                        raw_data=response_data,
                        estado='enviado',
                        config_utilizada=config
                    )
                except Exception as debug_error:
                    logger.warning(f'Error creando WebhookDebugMessage para outgoing: {debug_error}')
                
                # Actualizar conversación
                conversation.ultimo_mensaje_at = timezone.now()
                conversation.save()
                
                response = {'success': True, 'message_id': message_id}
            else:
                response = {
                    'success': False, 
                    'error': f"Error {response.status_code}: {response.text}"
                }
            
            if not response.get('success', False):
                error_msg = response.get('error_message', response.get('error', str(response)))
                return False, f"Error enviando mensaje: {error_msg}"
            
            # Ya creamos el mensaje arriba, solo necesitamos obtenerlo
            mensaje = conversation.mensajes.filter(
                contenido=content,
                direccion='outgoing',
                enviado_por=user
            ).order_by('-created_at').first()
            
            return True, mensaje
            
        except Exception as e:
            logger.error(f'Error enviando mensaje de texto: {str(e)}')
            return False, str(e)
    
    @staticmethod
    def send_media_message(conversation, file, caption, user):
        """
        Envía un mensaje con archivo multimedia
        """
        logger.info(f'🎬 Iniciando envío de multimedia para conversación {conversation.id}')
        logger.info(f'📁 Archivo: {file.name if file else "None"}, Usuario: {user.username}')
        
        try:
            config = WhatsAppConfig.objects.filter(is_active=True).first()
            if not config:
                logger.error('❌ No hay configuración activa de WhatsApp')
                return False, "No hay configuración activa de WhatsApp"
            
            # Validar archivo
            if not file:
                return False, "No se proporcionó archivo"
            
            # Validar tamaño
            max_size = 16 * 1024 * 1024  # 16MB
            if file.size > max_size:
                return False, "El archivo es demasiado grande (máximo 16MB)"
            
            # Guardar archivo temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_{file.name}') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            try:
                # Obtener configuración de WhatsApp
                config = WhatsAppConfig.objects.filter(is_active=True).first()
                if not config:
                    return False, "No hay configuración activa de WhatsApp"
                
                # Determinar tipo de media basado en el archivo
                media_type = 'document'  # Default para WhatsApp
                db_type = 'document'     # Default para BD
                
                if file.content_type:
                    if file.content_type.startswith('image/'):
                        media_type = 'image'
                        db_type = 'image'
                    elif file.content_type.startswith('audio/'):
                        media_type = 'audio'
                        db_type = 'audio'
                    elif file.content_type.startswith('video/'):
                        media_type = 'video'
                        db_type = 'video'
                
                # Envío directo a WhatsApp API
                try:
                    # Paso 1: Subir archivo a WhatsApp Media API
                    logger.info(f'📤 Subiendo archivo: {file.name}, tipo: {media_type}, tamaño: {file.size}')
                    
                    media_url = f"https://graph.facebook.com/v22.0/{config.phone_number_id}/media"
                    
                    # Preparar archivo para upload
                    with open(temp_path, 'rb') as file_data:
                        files = {
                            'file': (file.name, file_data, file.content_type or 'application/octet-stream')
                        }
                        
                        upload_data = {
                            'messaging_product': 'whatsapp',
                            'type': media_type
                        }
                        
                        # Headers solo con Authorization para upload
                        upload_headers = {
                            'Authorization': f'Bearer {config.access_token}'
                        }
                        
                        logger.info(f'📤 Subiendo a {media_url}...')
                        upload_response = requests.post(media_url, headers=upload_headers, data=upload_data, files=files)
                        upload_data_response = upload_response.json()
                        
                        logger.info(f'📥 Respuesta upload: Status {upload_response.status_code}, Data: {upload_data_response}')
                        
                        if upload_response.status_code != 200:
                            logger.error(f"❌ Error al subir archivo: {upload_data_response}")
                            return False, f"Error subiendo archivo: {upload_data_response.get('error', {}).get('message', 'Error desconocido')}"
                        
                        media_id = upload_data_response.get('id')
                        if not media_id:
                            logger.error(f"❌ No se obtuvo media_id del upload")
                            return False, "No se pudo obtener ID del archivo subido"
                        
                        logger.info(f'✅ Archivo subido exitosamente. Media ID: {media_id}')
                    
                    # Paso 2: Enviar mensaje usando el media_id
                    message_url = f"https://graph.facebook.com/v22.0/{config.phone_number_id}/messages"
                    
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": conversation.numero_whatsapp,
                        "type": media_type,
                        media_type: {
                            "id": media_id
                        }
                    }
                    
                    # Agregar caption si se proporciona y el tipo lo soporta
                    if caption and media_type in ['image', 'video', 'document']:
                        payload[media_type]["caption"] = caption
                    
                    # Agregar filename para documentos
                    if media_type == 'document' and file.name:
                        payload[media_type]["filename"] = file.name
                    
                    # Headers para envío de mensaje
                    message_headers = {
                        'Authorization': f'Bearer {config.access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    logger.info(f'📤 Enviando mensaje con media_id: {payload}')
                    response = requests.post(message_url, headers=message_headers, json=payload)
                    response_data = response.json()
                    logger.info(f'📥 Respuesta mensaje: Status {response.status_code}, Data: {response_data}')
                    
                    if response.status_code != 200:
                        logger.error(f"❌ Error al enviar mensaje: {response_data}")
                        return False, f"Error enviando mensaje: {response_data.get('error', {}).get('message', 'Error desconocido')}"
                    
                    # Crear respuesta compatible
                    response = {
                        'success': True,
                        'message_id': response_data.get('messages', [{}])[0].get('id'),
                        'media_id': media_id,
                        'response': response_data
                    }
                    
                    logger.info(f'📥 Respuesta WhatsApp API: {response}')
                    
                except Exception as whatsapp_error:
                    logger.error(f'❌ Error en WhatsApp API: {str(whatsapp_error)}')
                    return False, f"Error de WhatsApp: {str(whatsapp_error)}"
                
                if not response.get('success', False):
                    error_msg = response.get('error_message', response.get('error', str(response)))
                    logger.error(f'❌ Error de WhatsApp API: {error_msg}')
                    return False, f"Error enviando archivo: {error_msg}"
                
                # Crear mensaje en BD - Primero sin archivo
                mensaje = Mensaje.objects.create(
                    conversacion=conversation,
                    whatsapp_message_id=response.get('message_id', f"temp_{timezone.now().timestamp()}"),
                    contenido=caption or f"Archivo: {file.name}",
                    tipo=db_type,  # Usar tipo específico
                    direccion='outgoing',
                    estado='sent',
                    enviado_por=user,
                    timestamp_whatsapp=timezone.now(),
                    archivo_nombre=file.name,
                    archivo_tipo_mime=file.content_type,
                    archivo_tamaño=file.size,
                    caption=caption
                )
                
                # Guardar archivo localmente después de crear el mensaje
                try:
                    # Resetear posición del archivo al inicio
                    file.seek(0)
                    # Guardar el archivo en el campo archivo_local
                    mensaje.archivo_local.save(file.name, file, save=True)
                    logger.info(f'✅ Archivo guardado localmente: {mensaje.archivo_local.url}')
                except Exception as file_error:
                    logger.error(f'❌ Error guardando archivo localmente: {str(file_error)}')
                    # Mantener el mensaje pero sin archivo local
                
                # Actualizar conversación
                conversation.ultimo_mensaje_at = timezone.now()
                conversation.save()
                
                return True, mensaje
                
            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f'Error enviando archivo: {str(e)}')
            return False, str(e)
    
    @staticmethod
    def convert_audio_to_ogg(message_id):
        """
        Convierte audio a formato OGG para reproducción web
        """
        try:
            mensaje = Mensaje.objects.get(id=message_id)
            
            if not mensaje.archivo_local or mensaje.tipo != 'audio':
                return False, "No es un mensaje de audio válido"
            
            # Verificar si ya existe conversión
            ogg_path = mensaje.archivo_local.path.replace('.m4a', '.ogg').replace('.mp3', '.ogg')
            if os.path.exists(ogg_path):
                return True, ogg_path
            
            # Convertir usando ffmpeg
            input_path = mensaje.archivo_local.path
            
            # Comando ffmpeg para conversión optimizada
            cmd = [
                'ffmpeg', '-y',  # -y para sobrescribir
                '-i', input_path,
                '-c:a', 'libvorbis',  # Codec de audio Vorbis
                '-q:a', '4',  # Calidad media
                '-ac', '1',  # Mono
                '-ar', '22050',  # Sample rate reducido
                ogg_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f'Audio convertido: {input_path} -> {ogg_path}')
                return True, ogg_path
            else:
                logger.error(f'Error conversión audio: {result.stderr}')
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error(f'Timeout convirtiendo audio {message_id}')
            return False, "Timeout en conversión"
        except Exception as e:
            logger.error(f'Error convirtiendo audio {message_id}: {str(e)}')
            return False, str(e)
    
    @staticmethod
    def process_incoming_webhook_message(webhook_data):
        """
        Procesa un mensaje entrante del webhook de WhatsApp
        """
        try:
            # Extraer datos del webhook
            entry = webhook_data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            for message_data in messages:
                phone_number = message_data.get('from', '')
                message_type = message_data.get('type', 'text')
                timestamp = message_data.get('timestamp')
                
                # Buscar o crear cliente primero
                cliente, cliente_created = Cliente.objects.get_or_create(
                    numero_whatsapp=phone_number,
                    defaults={
                        'nombre': f'Cliente {phone_number}',
                        'apellido': '',
                        'origen': 'whatsapp',
                        'estado': 'prospecto'
                    }
                )
                
                # Buscar o crear conversación con cliente
                conversation, created = Conversacion.objects.get_or_create(
                    numero_whatsapp=phone_number,
                    defaults={
                        'cliente': cliente,
                        'estado': 'abierta',
                        'ultimo_mensaje_at': timezone.now()
                    }
                )
                
                # Si la conversación existe pero no tiene cliente, asignarlo
                if not conversation.cliente:
                    conversation.cliente = cliente
                    conversation.save()
                
                # Procesar contenido según tipo
                content = ""
                media_url = None
                
                if message_type == 'text':
                    content = message_data.get('text', {}).get('body', '')
                elif message_type in ['image', 'audio', 'video', 'document']:
                    media_data = message_data.get(message_type, {})
                    # Nuevo formato de WhatsApp: usar 'id' en lugar de 'url'
                    media_url = media_data.get('url') or media_data.get('id')
                    content = media_data.get('caption', f'Archivo {message_type}')
                
                # Crear mensaje
                # Convertir timestamp de WhatsApp a datetime timezone-aware
                timestamp_dt = None
                if timestamp:
                    try:
                        timestamp_dt = timezone.make_aware(datetime.fromtimestamp(int(timestamp)))
                    except (ValueError, TypeError):
                        timestamp_dt = timezone.now()
                else:
                    timestamp_dt = timezone.now()
                
                mensaje = Mensaje.objects.create(
                    conversacion=conversation,
                    contenido=content,
                    tipo=message_type,
                    direccion='incoming',
                    estado='received',
                    timestamp_whatsapp=timestamp_dt,
                    media_url=media_url or '',  # Asegurar que no sea None
                    whatsapp_message_id=message_data.get('id', '')
                )
                
                # Crear WebhookDebugMessage para mostrar en el historial de configuración
                try:
                    config = WhatsAppConfig.objects.filter(is_active=True).first()
                    WebhookDebugMessage.objects.create(
                        tipo='incoming',
                        numero_telefono=phone_number,
                        contenido=content,
                        raw_data=message_data,
                        estado='procesado',
                        config_utilizada=config
                    )
                except Exception as debug_error:
                    logger.warning(f'Error creando WebhookDebugMessage: {debug_error}')
                
                # Descargar y guardar archivo si es multimedia
                if media_url and message_type in ['image', 'audio', 'video', 'document']:
                    try:
                        MessageService._download_and_save_media(mensaje, media_url, message_type, media_data)
                    except Exception as download_error:
                        logger.error(f'⚠️ Error descargando archivo: {str(download_error)}')
                
                # Actualizar contadores
                conversation.mensajes_no_leidos += 1
                conversation.ultimo_mensaje_at = timezone.now()
                conversation.save()
                
                # NUEVA FUNCIONALIDAD: Crear lead automáticamente y asignar usando algoritmo
                try:
                    MessageService._create_lead_from_message(phone_number, content, message_type)
                except Exception as lead_error:
                    logger.error(f'⚠️ Error al crear lead automático: {str(lead_error)}')
                
                logger.info(f'Mensaje procesado: {phone_number} - {message_type}')
            
            return True, "Mensajes procesados correctamente"
            
        except Exception as e:
            logger.error(f'Error procesando webhook: {str(e)}')
            return False, str(e)
    
    @staticmethod
    def _create_lead_from_message(phone_number, content, message_type):
        """
        Crea un lead automáticamente desde un mensaje de WhatsApp y lo asigna usando el algoritmo
        """
        from ..models import Cliente, Lead, LeadAssignment
        from ..lead_distribution_service import LeadDistributionService
        
        # Limpiar número de teléfono (remover prefijo si existe)
        clean_phone = phone_number.replace('+', '').replace(' ', '')
        
        # Crear o obtener cliente
        cliente, created = Cliente.objects.get_or_create(
            numero_whatsapp=clean_phone,
            defaults={
                'nombre': f'Cliente {clean_phone}',
                'apellido': '',
                'origen': 'whatsapp',
                'estado': 'prospecto'
            }
        )
        
        if created:
            logger.info(f"📋 Cliente nuevo creado: {cliente.nombre_completo} ({clean_phone})")
        else:
            logger.info(f"📋 Cliente existente: {cliente.nombre_completo} ({clean_phone})")
        
        # Verificar si es un mensaje que debe generar lead
        if not MessageService._should_create_lead(content, message_type):
            logger.info(f"📝 Mensaje no genera lead: {content[:50] if content else 'Sin contenido'}...")
            return None
        
        # VERIFICACIÓN CRÍTICA: Cliente ya asignado a vendedor (90 días)
        from django.utils import timezone
        from datetime import timedelta
        
        # 1. Verificar si el cliente ya tiene una asignación activa (90 días)
        hace_90_dias = timezone.now() - timedelta(days=90)
        
        asignacion_existente = LeadAssignment.objects.filter(
            lead__cliente=cliente,
            assigned_date__gte=hace_90_dias,
            is_active=True
        ).order_by('-assigned_date').first()
        
        if asignacion_existente:
            dias_asignado = (timezone.now() - asignacion_existente.assigned_date).days
            logger.info(f"🔒 Cliente {cliente.numero_whatsapp} YA ESTÁ ASIGNADO a {asignacion_existente.organizational_unit.name} (hace {dias_asignado} días)")
            logger.info(f"    No se creará nuevo lead. Cliente pertenece a este vendedor por {90 - dias_asignado} días más.")
            
            # Buscar el lead activo más reciente
            lead_existente = asignacion_existente.lead
            return lead_existente
        
        # 2. Verificar si ya existe un lead reciente para este cliente (evitar duplicados del mismo día)
        recent_lead = Lead.objects.filter(
            cliente=cliente,
            fecha_primera_interaccion__gte=timezone.now() - timedelta(hours=24),
            is_active=True
        ).first()
        
        if recent_lead:
            logger.info(f"⏰ Lead reciente existe para {cliente.nombre_completo}, no crear duplicado")
            return recent_lead
        
        # Crear lead
        lead = Lead.objects.create(
            cliente=cliente,
            origen='whatsapp',
            prioridad='media',
            interes_inicial=content[:500] if content else 'Contacto inicial por WhatsApp',
            notas=f'Lead generado automáticamente desde mensaje WhatsApp. Tipo: {message_type}'
        )
        
        logger.info(f"✅ Lead creado: #{lead.id} para {cliente.nombre_completo}")
        
        # Asignar lead automáticamente usando el algoritmo Contador Acumulativo
        try:
            distribution_service = LeadDistributionService()
            assignment = distribution_service.assign_lead_to_sales_force(
                lead=lead,
                assigned_by_user=None,  # Sistema automático
                assignment_type='AUTOMATIC'
            )
            
            if assignment:
                logger.info(f"🎯 Lead #{lead.id} asignado a {assignment.organizational_unit.name}")
                print(f"🎯 LEAD ASIGNADO AUTOMÁTICAMENTE: #{lead.id} → {assignment.organizational_unit.name}")
            else:
                logger.warning(f"⚠️ No se pudo asignar lead #{lead.id}: no hay fuerzas de venta disponibles")
                
        except Exception as assignment_error:
            logger.error(f"❌ Error al asignar lead #{lead.id}: {str(assignment_error)}")
        
        return lead
    
    @staticmethod
    def _should_create_lead(content, message_type):
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
            'proyecto', 'planos', 'entrega', 'construcción', 'hola', 'buenos',
            'tardes', 'días', 'buenas', 'contacto', 'consulta', 'ayuda'
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
    
    @staticmethod
    def _download_and_save_media(mensaje, media_url_or_id, message_type, media_data):
        """
        Descarga y guarda localmente un archivo multimedia de WhatsApp
        Maneja tanto URLs directas como IDs de archivo
        """
        try:
            # Obtener configuración activa para el token
            config = WhatsAppConfig.objects.filter(is_active=True).first()
            if not config:
                logger.error("No hay configuración activa para descargar media")
                return False
            
            # Headers para la API de WhatsApp
            headers = {
                'Authorization': f'Bearer {config.access_token}',
            }
            
            # Si es un ID (formato nuevo), obtener información del archivo primero
            if media_url_or_id and not media_url_or_id.startswith('http'):
                # Es un ID de archivo, obtener información primero
                media_info_url = f"https://graph.facebook.com/v22.0/{media_url_or_id}"
                media_info_response = requests.get(media_info_url, headers=headers, timeout=30)
                
                if media_info_response.status_code != 200:
                    logger.error(f"Error obteniendo info de media con ID {media_url_or_id}: {media_info_response.status_code}")
                    return False
                
                media_info = media_info_response.json()
                download_url = media_info.get('url')
                mime_type = media_info.get('mime_type', 'application/octet-stream')
                
            else:
                # Es una URL directa (formato antiguo)
                download_url = media_url_or_id
                # Intentar obtener mime_type del media_data
                mime_type = media_data.get('mime_type', 'application/octet-stream')
            
            if not download_url:
                logger.error("No se encontró URL de descarga")
                return False
            
            # Descargar el archivo
            download_response = requests.get(download_url, headers=headers, timeout=60)
            if download_response.status_code != 200:
                logger.error(f"Error descargando archivo: {download_response.status_code}")
                return False
            
            # Generar nombre de archivo
            file_extension = MessageService._get_file_extension_from_mime(mime_type)
            filename = f"{message_type}_{mensaje.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
            
            # Guardar archivo
            from django.core.files.base import ContentFile
            file_content = ContentFile(download_response.content, name=filename)
            
            # Actualizar el mensaje con el archivo
            mensaje.archivo_local = file_content
            mensaje.archivo_tipo_mime = mime_type
            mensaje.archivo_nombre = media_data.get('filename', filename)
            mensaje.archivo_tamaño = len(download_response.content)
            mensaje.save()
            
            logger.info(f"Archivo descargado y guardado: {filename} ({len(download_response.content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error descargando archivo multimedia: {str(e)}")
            return False
    
    @staticmethod
    def _get_file_extension_from_mime(mime_type):
        """
        Obtiene la extensión de archivo basada en el tipo MIME
        """
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/3gpp': '.3gp',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/mp4': '.m4a',
            'audio/m4a': '.m4a',
            'audio/x-m4a': '.m4a',
            'audio/aac': '.aac',
            'audio/x-aac': '.aac',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'application/pdf': '.pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.ms-excel': '.xls',
            'text/plain': '.txt',
            'application/zip': '.zip',
            'application/x-rar-compressed': '.rar',
        }
        
        return mime_to_ext.get(mime_type, '.bin')