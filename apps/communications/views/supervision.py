# apps/communications/views/supervision.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from ..models import WhatsAppConfig, Conversacion, Lead, LeadAssignment
from ..services.chat_service import ChatService
from ..services.lead_service import LeadService
from ..utils.permissions import require_chat_supervision_access, api_require_chat_supervision_access
from ..utils.formatters import ResponseFormatter, DataFormatter
from ..utils.filters import ConversationFilters, PaginationHelper
from apps.sales_team_management.models import TeamMembership, HierarchyRelation
import logging

logger = logging.getLogger(__name__)


@login_required
@require_chat_supervision_access
def supervision_dashboard(request):
    """
    Dashboard principal de supervisión
    """
    # Verificar configuración activa
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa de WhatsApp Business')
        return redirect('communications:configuracion')
    
    # Obtener estadísticas generales para supervisión
    total_conversations = Conversacion.objects.filter(is_active=True).count()
    active_conversations = Conversacion.objects.filter(
        is_active=True, 
        estado='activa'
    ).count()
    unread_conversations = Conversacion.objects.filter(
        is_active=True,
        mensajes_no_leidos__gt=0
    ).count()
    
    # Estadísticas de leads
    total_leads = Lead.objects.filter(is_active=True).count()
    unassigned_leads = Lead.objects.filter(
        is_active=True,
        assignments__isnull=True
    ).count()
    
    # Conversaciones por equipo
    team_stats = []
    from apps.sales_team_management.models import OrganizationalUnit
    sales_teams = OrganizationalUnit.objects.filter(
        unit_type='SALES',
        is_active=True
    )
    
    for team in sales_teams:
        team_conversations = Conversacion.objects.filter(
            is_active=True,
            numero_whatsapp__in=Lead.objects.filter(
                assignments__organizational_unit=team,
                assignments__is_active=True
            ).values_list('cliente__numero_whatsapp', flat=True)
        ).count()
        
        team_stats.append({
            'team': team,
            'conversations': team_conversations
        })
    
    context = {
        'config': config,
        'stats': {
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'unread_conversations': unread_conversations,
            'total_leads': total_leads,
            'unassigned_leads': unassigned_leads
        },
        'team_stats': team_stats,
        'page_title': 'Dashboard de Supervisión',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Supervisión', 'url': None}
        ],
    }
    
    return render(request, 'communications/supervision_dashboard.html', context)


@login_required
@api_require_chat_supervision_access
def get_supervision_conversations(request):
    """
    API para obtener conversaciones para supervisión con filtros avanzados
    """
    try:
        # Verificar configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            return ResponseFormatter.error_response('No hay configuración activa', 400)
        
        # Obtener parámetros de filtro
        filters = {
            'estado': request.GET.get('estado'),
            'team_id': request.GET.get('team_id'),
            'assignment_status': request.GET.get('assignment_status'),
            'show_unread_only': request.GET.get('unread_only') == 'true',
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to')
        }
        
        # Usar el servicio específico de supervisión
        conversations, error = ChatService.get_conversations_for_supervision(request.user)
        
        if error:
            return ResponseFormatter.error_response(error, 400)
        
        # Aplicar filtros básicos
        if filters['estado']:
            conversations = conversations.filter(estado=filters['estado'])
        
        if filters['show_unread_only']:
            conversations = conversations.filter(mensajes_no_leidos__gt=0)
        
        if filters['date_from']:
            conversations = conversations.filter(created_at__date__gte=filters['date_from'])
        
        if filters['date_to']:
            conversations = conversations.filter(created_at__date__lte=filters['date_to'])
        
        # Limitar cantidad (sin paginación compleja por ahora)
        limit = min(int(request.GET.get('per_page', 20)), 100)
        conversations = conversations[:limit]
        
        # Formatear datos
        conversations_data = []
        for conv in conversations:
            conversation_data = ChatService.build_conversation_data(conv)
            conversations_data.append(conversation_data)
        
        response = JsonResponse({
            'success': True,  # Campo requerido por JavaScript
            'conversations': conversations_data,
            'total': len(conversations_data)
        })
        # Headers anti-caché
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
        
    except Exception as e:
        logger.error(f'Error obteniendo conversaciones de supervisión: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@api_require_chat_supervision_access
def get_team_performance(request):
    """
    API para obtener métricas de rendimiento por equipo
    """
    try:
        # Obtener parámetros de tiempo
        time_range = request.GET.get('time_range', 'week')  # day, week, month
        
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        if time_range == 'day':
            start_date = now.date()
        elif time_range == 'week':
            start_date = now.date() - timedelta(days=7)
        elif time_range == 'month':
            start_date = now.date() - timedelta(days=30)
        else:
            start_date = now.date() - timedelta(days=7)
        
        # Obtener equipos de ventas
        from apps.sales_team_management.models import OrganizationalUnit
        sales_teams = OrganizationalUnit.objects.filter(
            unit_type='SALES',
            is_active=True
        )
        
        team_performance = []
        
        for team in sales_teams:
            # Conversaciones del equipo
            team_leads = Lead.objects.filter(
                assignments__organizational_unit=team,
                assignments__is_active=True
            )
            
            team_phone_numbers = team_leads.values_list('cliente__numero_whatsapp', flat=True)
            
            team_conversations = Conversacion.objects.filter(
                numero_whatsapp__in=team_phone_numbers,
                is_active=True
            )
            
            # Métricas del período
            period_conversations = team_conversations.filter(
                created_at__date__gte=start_date
            )
            
            period_messages = 0
            for conv in period_conversations:
                period_messages += conv.mensajes.filter(
                    created_at__date__gte=start_date
                ).count()
            
            # Leads asignados en el período
            period_assignments = LeadAssignment.objects.filter(
                organizational_unit=team,
                is_active=True,
                assigned_date__date__gte=start_date
            ).count()
            
            # Miembros activos del equipo
            active_members = TeamMembership.objects.filter(
                organizational_unit=team,
                is_active=True,
                status='ACTIVE'
            ).count()
            
            team_performance.append({
                'team': {
                    'id': team.id,
                    'name': team.name
                },
                'metrics': {
                    'total_conversations': team_conversations.count(),
                    'period_conversations': period_conversations.count(),
                    'period_messages': period_messages,
                    'period_assignments': period_assignments,
                    'active_members': active_members,
                    'avg_conversations_per_member': (
                        team_conversations.count() / active_members if active_members > 0 else 0
                    )
                }
            })
        
        return ResponseFormatter.success_response({
            'teams': team_performance,
            'time_range': time_range,
            'start_date': start_date.isoformat()
        })
        
    except Exception as e:
        logger.error(f'Error obteniendo rendimiento de equipos: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@api_require_chat_supervision_access
def get_conversation_analytics(request, conversation_id):
    """
    API para obtener analytics detallados de una conversación
    """
    try:
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Estadísticas de mensajes
        total_messages = conversation.mensajes.count()
        incoming_messages = conversation.mensajes.filter(direccion='incoming').count()
        outgoing_messages = conversation.mensajes.filter(direccion='outgoing').count()
        
        # Tiempo de respuesta promedio
        from django.db.models import Avg
        response_times = []
        
        incoming_msgs = conversation.mensajes.filter(
            direccion='incoming'
        ).order_by('created_at')
        
        for incoming_msg in incoming_msgs:
            next_outgoing = conversation.mensajes.filter(
                direccion='outgoing',
                created_at__gt=incoming_msg.created_at
            ).order_by('created_at').first()
            
            if next_outgoing:
                response_time = (next_outgoing.created_at - incoming_msg.created_at).total_seconds()
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Información del lead asociado
        lead_info = None
        try:
            lead = Lead.objects.filter(
                cliente__numero_whatsapp=conversation.numero_whatsapp
            ).first()
            
            if lead:
                assignment = lead.assignments.filter(is_active=True).first()
                lead_info = {
                    'id': lead.id,
                    'estado': lead.estado,
                    'fecha_creacion': lead.created_at.isoformat(),
                    'assignment': DataFormatter.format_assignment_data(assignment) if assignment else None
                }
        except:
            pass
        
        analytics_data = {
            'conversation': DataFormatter.format_conversation_data(conversation),
            'message_stats': {
                'total_messages': total_messages,
                'incoming_messages': incoming_messages,
                'outgoing_messages': outgoing_messages,
                'response_ratio': outgoing_messages / incoming_messages if incoming_messages > 0 else 0,
                'avg_response_time_seconds': avg_response_time,
                'avg_response_time_minutes': avg_response_time / 60 if avg_response_time > 0 else 0
            },
            'lead_info': lead_info,
            'timeline': []
        }
        
        # Timeline de actividad (últimos mensajes)
        recent_messages = conversation.mensajes.order_by('-created_at')[:10]
        for msg in recent_messages:
            analytics_data['timeline'].append({
                'timestamp': msg.created_at.isoformat(),
                'type': msg.direccion,
                'content': msg.contenido[:100] + '...' if len(msg.contenido) > 100 else msg.contenido,
                'message_type': msg.tipo
            })
        
        return ResponseFormatter.success_response(analytics_data)
        
    except Exception as e:
        logger.error(f'Error obteniendo analytics de conversación {conversation_id}: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@api_require_chat_supervision_access
def get_supervision_conversation_messages(request, conversation_id):
    """
    API para obtener mensajes de conversación desde supervisión
    """
    try:
        # Usar el método específico para supervisión que ya incluye verificación de acceso
        from ..services.chat_service import ChatService
        result, error = ChatService.get_conversation_messages_for_supervision(conversation_id, request.user)
        
        if error:
            return ResponseFormatter.error_response(error, 403 if 'acceso' in error else 404)
        
        # Formato específico esperado por el JavaScript de supervisión
        response = JsonResponse({
            'success': True,
            'messages': result['messages'],
            'conversation': result['conversation']
        })
        # Headers anti-caché
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
        
    except Exception as e:
        logger.error(f'Error obteniendo mensajes de supervisión para conversación {conversation_id}: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_chat_supervision_access
def send_supervision_message(request):
    """
    API para enviar mensaje desde supervisión
    """
    try:
        import json
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        contenido = data.get('contenido')
        
        if not conversation_id or not contenido:
            return ResponseFormatter.error_response('Datos incompletos', 400)
        
        from django.shortcuts import get_object_or_404
        from ..models import Conversacion
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Enviar mensaje usando el servicio
        from ..services.message_service import MessageService
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
        logger.error(f'Error enviando mensaje de supervisión: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_chat_supervision_access
def send_supervision_media(request):
    """
    API para enviar archivos multimedia desde supervisión
    """
    try:
        conversation_id = request.POST.get('conversation_id')
        media_file = request.FILES.get('media_file')
        caption = request.POST.get('caption', '').strip()
        
        if not conversation_id or not media_file:
            return ResponseFormatter.error_response('Datos incompletos', 400)
        
        from django.shortcuts import get_object_or_404
        from ..models import Conversacion
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Validar archivo
        from ..utils.formatters import ValidationHelper
        is_valid, error = ValidationHelper.validate_file_upload(media_file)
        if not is_valid:
            return ResponseFormatter.error_response(error, 400)
        
        # Enviar archivo
        from ..services.message_service import MessageService
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
        logger.error(f'Error enviando archivo de supervisión: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_chat_supervision_access
def mark_supervision_conversation_read(request):
    """
    API para marcar conversación como leída desde supervisión
    """
    try:
        conversation_id = request.POST.get('conversation_id')
        
        if not conversation_id:
            return ResponseFormatter.error_response('ID de conversación requerido', 400)
        
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Para supervisión, acceso completo sin restricciones adicionales
        conversation.mensajes_no_leidos = 0
        conversation.save()
        
        return ResponseFormatter.success_response({
            'conversation_id': conversation_id,
            'marked_read': True
        }, 'Conversación marcada como leída')
        
    except Exception as e:
        logger.error(f'Error marcando conversación de supervisión como leída: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)