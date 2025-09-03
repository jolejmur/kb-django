# apps/communications/views/api_endpoints.py
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.models import User
from ..models import Conversacion, Lead, LeadAssignment
from ..services.message_service import MessageService
from ..services.lead_service import LeadService
from ..utils.permissions import (
    api_require_chat_supervision_access,
    api_require_chat_vendedor_access,
    api_require_lead_management_access
)
from ..utils.formatters import ResponseFormatter, ValidationHelper
from apps.sales_team_management.models import TeamMembership, OrganizationalUnit
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
@api_require_chat_supervision_access
def send_message(request):
    """
    API para enviar un mensaje (supervisión)
    """
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        contenido = data.get('contenido')
        
        if not conversation_id or not contenido:
            return ResponseFormatter.error_response('Datos incompletos', 400)
        
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Enviar mensaje usando el servicio
        success, result = MessageService.send_text_message(conversation, contenido, request.user)
        
        if success:
            return ResponseFormatter.success_response({
                'message_id': result.id,
                'timestamp': result.created_at.isoformat()
            }, 'Mensaje enviado exitosamente')
        else:
            return ResponseFormatter.error_response(result, 500)
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error al enviar mensaje: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_chat_vendedor_access
def send_vendedor_message(request):
    """
    API para enviar mensaje desde chat de vendedor
    """
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        contenido = data.get('contenido')
        
        if not conversation_id or not contenido:
            return ResponseFormatter.error_response('Datos incompletos', 400)
        
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Verificar acceso del vendedor (solo conversaciones asignadas específicamente)
        from ..services.chat_service import ChatService
        if not ChatService.user_has_conversation_access_for_chat(request.user, conversation):
            return ResponseFormatter.error_response('No tienes acceso a esta conversación', 403)
        
        # Enviar mensaje
        success, result = MessageService.send_text_message(conversation, contenido, request.user)
        
        if success:
            return ResponseFormatter.success_response({
                'message_id': result.id,
                'timestamp': result.created_at.isoformat()
            }, 'Mensaje enviado exitosamente')
        else:
            return ResponseFormatter.error_response(result, 500)
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error al enviar mensaje de vendedor: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_chat_vendedor_access
def send_vendedor_media(request):
    """
    API para enviar archivos multimedia desde chat de vendedor
    """
    try:
        # Imports necesarios
        from django.utils import timezone
        from ..models import Mensaje
        from ..services.message_service import MessageService
        
        conversation_id = request.POST.get('conversation_id')
        media_file = request.FILES.get('media_file')
        caption = request.POST.get('caption', '').strip()
        
        if not conversation_id or not media_file:
            return ResponseFormatter.error_response('Datos incompletos', 400)
        
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Verificar acceso del vendedor
        from ..services.chat_service import ChatService
        if not ChatService.user_has_conversation_access_for_chat(request.user, conversation):
            return ResponseFormatter.error_response('No tienes acceso a esta conversación', 403)
        
        # Validar archivo
        from ..utils.formatters import ValidationHelper
        is_valid, error = ValidationHelper.validate_file_upload(media_file)
        if not is_valid:
            return ResponseFormatter.error_response(error, 400)
        
        # Enviar archivo usando el servicio completo
        success, result = MessageService.send_media_message(conversation, media_file, caption, request.user)
        
        if success:
            return ResponseFormatter.success_response({
                'message_id': result.id,
                'timestamp': result.created_at.isoformat(),
                'file_name': result.archivo_nombre
            }, 'Archivo enviado exitosamente')
        else:
            return ResponseFormatter.error_response(result, 500)
        
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        return ResponseFormatter.error_response(error_msg, 500)


@login_required
@require_http_methods(["POST"])
@api_require_lead_management_access
def update_lead_distribution(request):
    """
    API para actualizar configuración de distribución de leads
    """
    try:
        data = json.loads(request.body)
        
        # Solo superusuarios pueden modificar la configuración
        if not request.user.is_superuser:
            return ResponseFormatter.error_response('Sin permisos para modificar configuración', 403)
        
        config = LeadService.get_distribution_config()
        if not config:
            return ResponseFormatter.error_response('Error al obtener configuración', 500)
        
        # Actualizar campos permitidos
        if 'distribution_method' in data:
            config.distribution_method = data['distribution_method']
        if 'auto_assign' in data:
            config.auto_assign = data['auto_assign']
        if 'max_leads_per_day' in data:
            config.max_leads_per_day = data['max_leads_per_day']
        
        config.save()
        
        return ResponseFormatter.success_response(
            {'config_id': config.id},
            'Configuración actualizada exitosamente'
        )
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error actualizando configuración: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_lead_management_access
def assign_lead_to_salesperson(request):
    """
    API para asignar un lead a un vendedor específico
    """
    try:
        data = json.loads(request.body)
        logger.info(f'🔍 DEBUG: Datos recibidos en assign_lead_to_salesperson: {data}')
        
        lead_id = data.get('lead_id')
        user_id = data.get('user_id') or data.get('salesperson_id')  # Compatibilidad con frontend
        notes = data.get('notes', '')
        assignment_type = data.get('assignment_type', 'MANUAL')
        
        logger.info(f'🔍 DEBUG: lead_id={lead_id}, user_id={user_id}, notes={notes}, assignment_type={assignment_type}')
        
        if not lead_id or not user_id:
            logger.error(f'❌ Datos incompletos: lead_id={lead_id}, user_id={user_id}')
            return ResponseFormatter.error_response('Datos incompletos: lead_id y user_id requeridos', 400)
        
        # Asignar lead usando el servicio
        success, message = LeadService.assign_lead_to_user(lead_id, user_id, request.user)
        
        if success:
            return ResponseFormatter.success_response(
                {'lead_id': lead_id, 'user_id': user_id},
                message
            )
        else:
            return ResponseFormatter.error_response(message, 400)
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error asignando lead: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@api_require_lead_management_access
def get_sales_team_members(request, unit_id):
    """
    API para obtener miembros de un equipo de ventas
    """
    try:
        unit = get_object_or_404(OrganizationalUnit, id=unit_id, unit_type='SALES')
        
        # Verificar acceso del usuario
        team_info = LeadService.get_user_team_info(request.user)
        
        # Si el usuario tiene equipo específico, solo puede ver su propio equipo
        if team_info['is_team_member'] and team_info['user_team'] and team_info['user_team'].id != unit.id:
            return ResponseFormatter.error_response('Sin acceso a este equipo', 403)
        
        # Si el usuario NO tiene equipo específico (admin, etc.), puede acceder a cualquier equipo
        # Si el usuario SÍ pertenece al equipo solicitado, puede acceder
        
        # Obtener miembros activos
        members = TeamMembership.objects.filter(
            organizational_unit=unit,
            is_active=True,
            status='ACTIVE'
        ).select_related('user')
        
        members_data = []
        for membership in members:
            members_data.append({
                'id': membership.user.id,
                'name': membership.user.get_full_name(),
                'username': membership.user.username,
                'position': membership.position_type.name if membership.position_type else None,
                'email': membership.user.email
            })
        
        return ResponseFormatter.success_response({
            'team': {
                'id': unit.id,
                'name': unit.name
            },
            'members': members_data,
            'salespeople': members_data  # Para compatibilidad con frontend
        })
        
    except Exception as e:
        logger.error(f'Error obteniendo miembros del equipo {unit_id}: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_lead_management_access
def reject_lead(request, lead_id):
    """
    API para rechazar un lead
    """
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '')
        
        # Rechazar lead usando el servicio
        success, message = LeadService.reject_lead(lead_id, request.user, reason)
        
        if success:
            return ResponseFormatter.success_response(
                {'lead_id': lead_id},
                message
            )
        else:
            return ResponseFormatter.error_response(message, 400)
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error rechazando lead {lead_id}: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@api_require_lead_management_access
def manual_lead_assignment(request):
    """
    API para asignación manual de leads
    """
    try:
        if request.method == 'GET':
            # Obtener leads disponibles para asignación manual
            team_info = LeadService.get_user_team_info(request.user)
            
            # Obtener leads sin asignar o asignados al equipo pero sin usuario específico
            available_leads = Lead.objects.filter(
                is_active=True,
                assignments__isnull=False,
                assignments__is_active=True,
                assignments__assigned_to_user__isnull=True
            )
            
            # Filtrar por equipo si corresponde
            if team_info['is_team_member']:
                available_leads = available_leads.filter(
                    assignments__organizational_unit=team_info['user_team']
                )
            
            available_leads = available_leads.select_related('cliente').distinct()[:50]
            
            leads_data = []
            for lead in available_leads:
                leads_data.append({
                    'id': lead.id,
                    'cliente_nombre': lead.cliente.nombre_completo,
                    'cliente_telefono': lead.cliente.numero_whatsapp,
                    'estado': lead.estado,
                    'fecha_creacion': lead.created_at.isoformat()
                })
            
            return ResponseFormatter.success_response({
                'leads': leads_data,
                'total': len(leads_data)
            })
        
        elif request.method == 'POST':
            # Procesar asignación manual
            data = json.loads(request.body)
            assignments = data.get('assignments', [])
            
            if not assignments:
                return ResponseFormatter.error_response('No se proporcionaron asignaciones', 400)
            
            results = []
            for assignment in assignments:
                lead_id = assignment.get('lead_id')
                user_id = assignment.get('user_id')
                
                success, message = LeadService.assign_lead_to_user(lead_id, user_id, request.user)
                results.append({
                    'lead_id': lead_id,
                    'user_id': user_id,
                    'success': success,
                    'message': message
                })
            
            successful_assignments = len([r for r in results if r['success']])
            
            return ResponseFormatter.success_response({
                'results': results,
                'successful_assignments': successful_assignments,
                'total_assignments': len(results)
            }, f'Procesadas {successful_assignments} de {len(results)} asignaciones')
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error en asignación manual: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)