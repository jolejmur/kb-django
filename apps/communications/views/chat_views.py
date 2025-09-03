# apps/communications/views/chat_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from ..models import WhatsAppConfig, Conversacion, Lead
from ..services.chat_service import ChatService
from ..utils.permissions import (
    require_chat_supervision_access, 
    require_chat_vendedor_access,
    api_require_chat_supervision_access,
    api_require_chat_vendedor_access
)
from ..utils.formatters import ResponseFormatter, DataFormatter
import logging

logger = logging.getLogger(__name__)


@login_required
@require_chat_supervision_access
def supervision_chat(request):
    """
    Vista de supervisión jerárquica - Para gerentes y supervisores
    """
    # Verificar si hay configuración activa
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa de WhatsApp Business')
        return redirect('communications:configuracion')
    
    context = {
        'config': config,
        'user': request.user,
        'is_supervision': True,
        'page_title': 'Supervisión de Chat',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Supervisión Chat', 'url': None}
        ],
    }
    
    return render(request, 'communications/supervision/supervision_chat.html', context)


@login_required
@require_chat_vendedor_access
def chat_vendedor(request):
    """
    Vista de chat para vendedores - Solo ven sus leads asignados
    """
    # Verificar si hay configuración activa
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa de WhatsApp Business')
        return redirect('communications:configuracion')
    
    # Obtener información del equipo del usuario
    accessible_leads = ChatService.get_user_accessible_leads_for_chat(request.user)
    
    # Obtener conversaciones activas de los leads accesibles (solo asignados al usuario)
    conversations, error = ChatService.get_conversations_for_chat(request.user)
    
    if error:
        messages.error(request, error)
        return redirect('communications:configuracion')
    
    # Estadísticas básicas
    total_conversations = conversations.count()
    active_conversations = conversations.filter(estado='abierta').count()
    
    context = {
        'page_title': 'Chat - Mis Leads',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Chat', 'url': None}
        ],
        'config': config,
        'conversations': conversations,
        'total_conversations': total_conversations,
        'active_conversations': active_conversations,
        'accessible_leads_count': len(accessible_leads),
        'has_active_config': bool(config),
    }
    
    response = render(request, 'communications/vendedor/chat_vendedor.html', context)
    # Headers anti-caché para evitar problemas con JavaScript cached
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
@api_require_chat_supervision_access
def get_conversations(request):
    """
    API para obtener conversaciones para supervisión
    """
    try:
        # Verificar configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            return ResponseFormatter.error_response('No hay configuración activa', 400)
        
        # Obtener parámetros de filtro
        estado = request.GET.get('estado', 'todos')
        limit = int(request.GET.get('limit', 20))
        
        # Para supervisión, obtener conversaciones basadas en jerarquía
        conversations, error = ChatService.get_conversations_for_supervision(request.user)
        
        if error:
            return ResponseFormatter.error_response(error, 400)
        
        # Aplicar filtros
        if estado != 'todos':
            conversations = conversations.filter(estado=estado)
        
        # Ordenar y limitar
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
        logger.error(f'Error obteniendo conversaciones para supervisión: {str(e)}')
        return ResponseFormatter.error_response(str(e), 500)


@login_required
@api_require_chat_vendedor_access
def get_vendedor_conversations(request):
    """
    API para obtener conversaciones del vendedor - Solo sus leads asignados
    """
    try:
        # Obtener conversaciones accesibles para el usuario (solo asignadas específicamente)
        conversations, error = ChatService.get_conversations_for_chat(request.user)
        
        if error:
            return ResponseFormatter.error_response(error, 400)
        
        # Formatear datos de conversaciones
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
        logger.error(f'Error obteniendo conversaciones de vendedor: {str(e)}')
        return ResponseFormatter.error_response(str(e), 500)


@login_required
@api_require_chat_supervision_access
def get_conversation_messages(request, conversation_id):
    """
    API para obtener mensajes de una conversación (supervisión)
    """
    try:
        # Para supervisión, acceso completo a todas las conversaciones
        result, error = ChatService.get_conversation_messages(conversation_id, request.user)
        
        if error:
            return ResponseFormatter.error_response(error, 403 if 'acceso' in error else 404)
        
        return ResponseFormatter.success_response(result)
        
    except Exception as e:
        logger.error(f'Error obteniendo mensajes de conversación {conversation_id}: {str(e)}')
        return ResponseFormatter.error_response(str(e), 500)


@login_required  
@api_require_chat_vendedor_access
def get_vendedor_conversation_messages(request, conversation_id):
    """
    API para obtener mensajes de una conversación - Solo si el vendedor tiene acceso
    """
    try:
        # Verificar acceso usando método específico para chat vendedor
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        if not ChatService.user_has_conversation_access_for_chat(request.user, conversation):
            return ResponseFormatter.error_response('No tienes acceso a esta conversación', 403)
        
        # Obtener mensajes
        result, error = ChatService.get_conversation_messages(conversation_id, request.user)
        
        if error:
            return ResponseFormatter.error_response(error, 403 if 'acceso' in error else 404)
        
        return ResponseFormatter.success_response(result)
        
    except Exception as e:
        logger.error(f'Error obteniendo mensajes de vendedor para conversación {conversation_id}: {str(e)}')
        return ResponseFormatter.error_response(str(e), 500)


@login_required
@require_http_methods(["POST"])
@api_require_chat_vendedor_access
def mark_vendedor_conversation_read(request):
    """
    API para marcar conversación como leída - Solo para vendedores
    """
    try:
        conversation_id = request.POST.get('conversation_id')
        
        if not conversation_id:
            return ResponseFormatter.error_response('ID de conversación requerido', 400)
        
        # Verificar que el vendedor tiene acceso a esta conversación
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        if not ChatService.user_has_conversation_access_for_chat(request.user, conversation):
            return ResponseFormatter.error_response('No tienes acceso a esta conversación', 403)
        
        # Marcar mensajes como leídos
        conversation.mensajes_no_leidos = 0
        conversation.save()
        
        return ResponseFormatter.success_response({
            'conversation_id': conversation_id,
            'marked_read': True
        }, 'Conversación marcada como leída')
        
    except Exception as e:
        logger.error(f'Error marcando conversación como leída: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)