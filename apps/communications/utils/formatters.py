# apps/communications/utils/formatters.py
from django.http import JsonResponse
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Utilidades para formatear respuestas
    """
    
    @staticmethod
    def success_response(data=None, message=None):
        """
        Formatea respuesta exitosa
        """
        response_data = {'success': True}
        
        if data is not None:
            response_data['data'] = data
        
        if message:
            response_data['message'] = message
        
        return JsonResponse(response_data)
    
    @staticmethod
    def error_response(message, status=400, error_code=None):
        """
        Formatea respuesta de error
        """
        response_data = {
            'success': False,
            'error': message
        }
        
        if error_code:
            response_data['error_code'] = error_code
        
        return JsonResponse(response_data, status=status)
    
    @staticmethod
    def paginated_response(pagination_data, message=None):
        """
        Formatea respuesta paginada
        """
        response_data = {
            'success': True,
            'data': pagination_data['items'],
            'pagination': {
                'page': pagination_data['page'],
                'per_page': pagination_data['per_page'],
                'total': pagination_data['total'],
                'total_pages': pagination_data['total_pages'],
                'has_next': pagination_data['has_next'],
                'has_previous': pagination_data['has_previous']
            }
        }
        
        if message:
            response_data['message'] = message
        
        return JsonResponse(response_data)


class DataFormatter:
    """
    Utilidades para formatear datos
    """
    
    @staticmethod
    def format_lead_data(lead):
        """
        Formatea datos de un lead
        """
        assignment = lead.assignments.filter(is_active=True).first()
        
        return {
            'id': lead.id,
            'cliente': {
                'id': lead.cliente.id,
                'nombre_completo': lead.cliente.nombre_completo,
                'numero_whatsapp': lead.cliente.numero_whatsapp,
                'estado': lead.cliente.estado
            },
            'estado': lead.estado,
            'fecha_creacion': lead.created_at.isoformat(),
            'notas': lead.notas,
            'assignment': DataFormatter.format_assignment_data(assignment) if assignment else None
        }
    
    @staticmethod
    def format_assignment_data(assignment):
        """
        Formatea datos de una asignación
        """
        if not assignment:
            return None
        
        return {
            'id': assignment.id,
            'organizational_unit': {
                'id': assignment.organizational_unit.id,
                'name': assignment.organizational_unit.name
            } if assignment.organizational_unit else None,
            'assigned_to_user': {
                'id': assignment.assigned_to_user.id,
                'name': assignment.assigned_to_user.get_full_name(),
                'username': assignment.assigned_to_user.username
            } if assignment.assigned_to_user else None,
            'assigned_by': {
                'id': assignment.assigned_by.id,
                'name': assignment.assigned_by.get_full_name()
            } if assignment.assigned_by else None,
            'assigned_at': assignment.assigned_date.isoformat() if assignment.assigned_date else None,
            'is_active': assignment.is_active
        }
    
    @staticmethod
    def format_conversation_data(conversation):
        """
        Formatea datos de una conversación
        """
        last_message = conversation.mensajes.order_by('-created_at').first()
        
        return {
            'id': conversation.id,
            'cliente': {
                'id': conversation.cliente.id,
                'nombre_completo': conversation.cliente.nombre_completo
            } if conversation.cliente else None,
            'numero_whatsapp': conversation.numero_whatsapp,
            'estado': conversation.estado,
            'mensajes_no_leidos': conversation.mensajes_no_leidos,
            'ultimo_mensaje_at': conversation.ultimo_mensaje_at.isoformat() if conversation.ultimo_mensaje_at else None,
            'ultimo_mensaje_preview': DataFormatter.format_message_preview(last_message),
            'created_at': conversation.created_at.isoformat()
        }
    
    @staticmethod
    def format_message_data(message):
        """
        Formatea datos de un mensaje
        """
        return {
            'id': message.id,
            'contenido': message.contenido,
            'tipo': message.tipo,
            'direccion': message.direccion,
            'estado': message.estado,
            'timestamp_whatsapp': message.timestamp_whatsapp.isoformat() if message.timestamp_whatsapp else None,
            'created_at': message.created_at.isoformat(),
            'enviado_por': {
                'id': message.enviado_por.id,
                'name': message.enviado_por.get_full_name()
            } if message.enviado_por else None,
            'media_url': message.media_url,
            'archivo_local': message.archivo_local.url if message.archivo_local else None,
            'archivo_tipo_mime': message.archivo_tipo_mime,
            'archivo_nombre': message.archivo_nombre,
            'archivo_tamaño': message.archivo_tamaño,
            'caption': getattr(message, 'caption', None)
        }
    
    @staticmethod
    def format_message_preview(message):
        """
        Formatea preview de mensaje
        """
        if not message:
            return ''
        
        content = message.contenido or ''
        
        # Truncar si es muy largo
        if len(content) > 50:
            return content[:50] + '...'
        
        return content
    
    @staticmethod
    def format_stats_data(stats):
        """
        Formatea datos de estadísticas
        """
        return {
            'leads': {
                'total': stats.get('total_leads', 0),
                'by_status': {
                    'nuevos': stats.get('nuevos', 0),
                    'contactados': stats.get('contactados', 0),
                    'calificados': stats.get('calificados', 0),
                    'perdidos': stats.get('perdidos', 0)
                },
                'assignments': {
                    'asignados': stats.get('asignados', 0),
                    'no_asignados': stats.get('no_asignados', 0)
                }
            },
            'time_stats': {
                'hoy': stats.get('leads_hoy', 0),
                'semana': stats.get('leads_semana', 0),
                'mes': stats.get('leads_mes', 0)
            }
        }


class ValidationHelper:
    """
    Utilidades para validación de datos
    """
    
    @staticmethod
    def validate_phone_number(phone_number):
        """
        Valida formato de número de teléfono
        """
        if not phone_number:
            return False, "Número de teléfono requerido"
        
        # Remover espacios y caracteres especiales
        clean_number = ''.join(filter(str.isdigit, phone_number))
        
        # Validar longitud
        if len(clean_number) < 10 or len(clean_number) > 15:
            return False, "Número de teléfono debe tener entre 10 y 15 dígitos"
        
        return True, clean_number
    
    @staticmethod
    def validate_file_upload(file):
        """
        Valida archivo subido
        """
        if not file:
            return False, "Archivo requerido"
        
        # Validar tamaño (16MB máximo)
        max_size = 16 * 1024 * 1024
        if file.size > max_size:
            return False, "Archivo demasiado grande (máximo 16MB)"
        
        # Mapear tipos MIME comunes a los soportados por WhatsApp
        mime_mapping = {
            'audio/x-m4a': 'audio/mp4',
            'audio/m4a': 'audio/mp4', 
            'audio/mp3': 'audio/mpeg',
            'image/jpg': 'image/jpeg',
            'video/3g': 'video/3gpp'
        }
        
        # Aplicar mapeo si es necesario
        original_mime = file.content_type
        mapped_mime = mime_mapping.get(original_mime, original_mime)
        
        # Validar tipo MIME permitido (según WhatsApp Business API)
        allowed_types = [
            # Audio - Solo los soportados por WhatsApp
            'audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/amr', 'audio/ogg', 'audio/opus',
            # Documentos - Solo los soportados por WhatsApp  
            'application/vnd.ms-powerpoint', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/pdf', 'text/plain', 'application/vnd.ms-excel',
            # Imágenes - Solo las soportadas por WhatsApp
            'image/jpeg', 'image/png', 'image/webp',
            # Video - Solo los soportados por WhatsApp
            'video/mp4', 'video/3gpp'
        ]
        
        if mapped_mime not in allowed_types:
            return False, f"Tipo de archivo no soportado por WhatsApp: {original_mime}"
        
        # Si se aplicó un mapeo, actualizar el content_type del archivo
        if mapped_mime != original_mime:
            file.content_type = mapped_mime
        
        return True, None