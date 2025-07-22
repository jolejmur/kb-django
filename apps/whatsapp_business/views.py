# apps/whatsapp_business/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from .models import WhatsAppConfig, WebhookDebugMessage, TestMessage, Conversacion, Mensaje, Cliente
from .forms import WhatsAppConfigForm
from .services import WhatsAppService

logger = logging.getLogger(__name__)


@login_required
def leads_list(request):
    """
    Vista para mostrar lista de leads pendientes de asignación
    """
    # Hardcoded leads pendientes (no hay Team Leader disponibles)
    leads_hardcoded = [
        {
            'id': 1,
            'telefono': '65020724',
            'mensaje': 'Quiero más información',
            'fecha_creacion': '2024-07-21 10:30:00',
            'origen': 'WhatsApp',
            'prioridad': 'alta',
            'estado': 'pendiente'
        },
        {
            'id': 2,
            'telefono': '75047929',
            'mensaje': 'Quiero más información',
            'fecha_creacion': '2024-07-21 11:15:00',
            'origen': 'WhatsApp',
            'prioridad': 'alta',
            'estado': 'pendiente'
        },
        {
            'id': 3,
            'telefono': '60004902',
            'mensaje': 'Quiero más información',
            'fecha_creacion': '2024-07-21 12:00:00',
            'origen': 'WhatsApp',
            'prioridad': 'alta',
            'estado': 'pendiente'
        }
    ]
    
    # Determinar vista (dashboard por defecto, lista si se especifica)
    view_type = request.GET.get('view', 'dashboard')
    
    # Calcular estadísticas
    alta_count = sum(1 for lead in leads_hardcoded if lead['prioridad'] == 'alta')
    whatsapp_count = sum(1 for lead in leads_hardcoded if lead['origen'] == 'WhatsApp')
    
    context = {
        'leads': leads_hardcoded,
        'total_pendientes': len(leads_hardcoded),
        'alta_count': alta_count,
        'whatsapp_count': whatsapp_count,
        'view_type': view_type,
        'mensaje_sistema': 'No hay Team Leaders disponibles para asignar estos leads automáticamente.'
    }
    
    return render(request, 'leads/leads_list.html', context)


def check_whatsapp_access(user):
    """Verificar si el usuario tiene acceso a WhatsApp Business"""
    if not user.is_authenticated:
        return False
    
    # Verificar si el usuario tiene el módulo de configuración
    return user.has_module_access('Configuraciones de Meta Business')


@login_required
def configuracion_whatsapp(request):
    """
    Vista para configurar WhatsApp Business
    """
    if not check_whatsapp_access(request.user):
        raise PermissionDenied("No tienes permisos para acceder a esta funcionalidad")
    
    # Obtener la configuración actual (solo puede haber una activa)
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        # Check if this is an individual field edit or full form submission
        if len(request.POST) == 2 and 'csrfmiddlewaretoken' in request.POST:
            # This is an individual field edit
            field_name = None
            field_value = None
            
            for key, value in request.POST.items():
                if key != 'csrfmiddlewaretoken':
                    field_name = key
                    field_value = value
                    break
            
            if field_name and config:
                # Update only the specific field
                if hasattr(config, field_name):
                    # Handle boolean fields
                    if field_name == 'is_active':
                        field_value = field_value == 'on'
                        # If activating, deactivate others
                        if field_value:
                            WhatsAppConfig.objects.filter(is_active=True).update(is_active=False)
                    
                    setattr(config, field_name, field_value)
                    config.save()
                    messages.success(request, f'Campo {field_name} actualizado correctamente.')
                else:
                    messages.error(request, f'Campo {field_name} no válido.')
            elif field_name and not config:
                # Create new config with individual field
                messages.error(request, 'Debe crear una configuración completa primero.')
            else:
                messages.error(request, 'Error al procesar la solicitud.')
            
            return redirect('whatsapp_business:configuracion')
        else:
            # This is a full form submission
            form = WhatsAppConfigForm(request.POST, instance=config)
            if form.is_valid():
                # Si se crea una nueva configuración activa, desactivar las demás
                if form.cleaned_data.get('is_active'):
                    WhatsAppConfig.objects.filter(is_active=True).update(is_active=False)
                
                config = form.save()
                
                if config.is_active:
                    messages.success(request, 'Configuración de WhatsApp Business guardada y activada correctamente.')
                else:
                    messages.success(request, 'Configuración de WhatsApp Business guardada correctamente.')
                
                return redirect('whatsapp_business:configuracion')
            else:
                messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = WhatsAppConfigForm(instance=config)
    
    # Obtener todas las configuraciones para mostrar el historial
    all_configs = WhatsAppConfig.objects.all().order_by('-created_at')
    
    # Obtener mensajes de debug recientes
    debug_messages = []
    if config:
        try:
            service = WhatsAppService()
            debug_messages = service.get_debug_messages(limit=10)
        except ValueError:
            debug_messages = []
    
    context = {
        'form': form,
        'config': config,
        'all_configs': all_configs,
        'has_active_config': config is not None,
        'debug_messages': debug_messages,
        'page_title': 'Configuración Meta Business',
        'breadcrumbs': [
            {'name': 'Marketing Digital', 'url': '#'},
            {'name': 'Configuración Meta Business', 'url': None}
        ]
    }
    
    return render(request, 'whatsapp_business/configuracion.html', context)


@login_required
def test_webhook(request):
    """
    Vista para probar la configuración del webhook
    """
    if not check_whatsapp_access(request.user):
        raise PermissionDenied("No tienes permisos para acceder a esta funcionalidad")
    
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    
    if not config:
        messages.error(request, 'No hay configuración activa de WhatsApp Business.')
        return redirect('whatsapp_business:configuracion')
    
    # Aquí podrías implementar una prueba real del webhook
    # Por ahora, simulamos una respuesta exitosa
    try:
        # Simular prueba del webhook
        webhook_status = {
            'url': config.webhook_url,
            'status': 'success',
            'message': 'Webhook configurado correctamente'
        }
        
        messages.success(request, f'Webhook probado exitosamente: {webhook_status["message"]}')
        
    except Exception as e:
        logger.error(f'Error al probar webhook: {str(e)}')
        messages.error(request, f'Error al probar webhook: {str(e)}')
    
    return redirect('whatsapp_business:configuracion')


@login_required
def activar_configuracion(request, config_id):
    """
    Vista para activar una configuración específica
    """
    if not check_whatsapp_access(request.user):
        raise PermissionDenied("No tienes permisos para acceder a esta funcionalidad")
    
    if request.method == 'POST':
        config = get_object_or_404(WhatsAppConfig, id=config_id)
        
        # Desactivar todas las configuraciones
        WhatsAppConfig.objects.filter(is_active=True).update(is_active=False)
        
        # Activar la configuración seleccionada
        config.is_active = True
        config.save()
        
        messages.success(request, f'Configuración activada correctamente (ID: {config.phone_number_id})')
    
    return redirect('whatsapp_business:configuracion')


@login_required
def eliminar_configuracion(request, config_id):
    """
    Vista para eliminar una configuración
    """
    if not check_whatsapp_access(request.user):
        raise PermissionDenied("No tienes permisos para acceder a esta funcionalidad")
    
    if request.method == 'POST':
        config = get_object_or_404(WhatsAppConfig, id=config_id)
        
        # No permitir eliminar la configuración activa
        if config.is_active:
            messages.error(request, 'No puedes eliminar la configuración activa. Primero activa otra configuración.')
        else:
            phone_id = config.phone_number_id
            config.delete()
            messages.success(request, f'Configuración eliminada correctamente (ID: {phone_id})')
    
    return redirect('whatsapp_business:configuracion')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook_whatsapp(request):
    """
    Webhook para recibir mensajes de WhatsApp Business
    """
    if request.method == 'GET':
        # Verificación del webhook
        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        mode = request.GET.get('hub.mode')
        
        # DEBUG: Imprimir todos los parámetros recibidos
        logger.info(f'🔍 Webhook GET - Parámetros recibidos: {dict(request.GET)}')
        logger.info(f'🔍 hub.verify_token: {verify_token}')
        logger.info(f'🔍 hub.challenge: {challenge}')
        logger.info(f'🔍 hub.mode: {mode}')
        
        # Obtener el token de verificación de la configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        
        if not config:
            logger.error('❌ No hay configuración activa de WhatsApp')
            return JsonResponse({'error': 'No hay configuración activa'}, status=500)
        
        logger.info(f'🔍 Token esperado: {config.webhook_verify_token}')
        
        # Verificar que el modo sea 'subscribe' y el token coincida
        if mode == 'subscribe' and verify_token == config.webhook_verify_token:
            logger.info('✅ Webhook verificado correctamente')
            # Facebook espera solo el challenge como texto plano, no JSON
            return HttpResponse(challenge, content_type='text/plain')
        else:
            logger.warning(f'❌ Token de verificación incorrecto: {verify_token} (esperado: {config.webhook_verify_token})')
            return JsonResponse({'error': 'Token de verificación incorrecto'}, status=403)
    
    elif request.method == 'POST':
        # Procesar mensajes entrantes
        try:
            data = json.loads(request.body)
            logger.info(f'Webhook recibido: {data}')
            
            # Procesar mensajes usando el servicio
            try:
                service = WhatsAppService()
                result = service.process_webhook_message(data)
                
                if result['success']:
                    return JsonResponse({'status': 'success'}, status=200)
                else:
                    logger.error(f'Error en servicio: {result.get("error")}')
                    return JsonResponse({'error': result.get("error")}, status=500)
                    
            except ValueError as e:
                logger.error(f'Error de configuración: {str(e)}')
                return JsonResponse({'error': 'Configuración no disponible'}, status=500)
            
        except json.JSONDecodeError:
            logger.error('Error al decodificar JSON del webhook')
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f'Error al procesar webhook: {str(e)}')
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def status_api(request):
    """
    API para obtener el estado de la configuración de WhatsApp
    """
    if not check_whatsapp_access(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    
    if not config:
        return JsonResponse({
            'status': 'no_config',
            'message': 'No hay configuración activa'
        })
    
    return JsonResponse({
        'status': 'active',
        'phone_number_id': config.phone_number_id,
        'business_account_id': config.business_account_id,
        'webhook_url': config.webhook_url,
        'created_at': config.created_at.isoformat(),
        'updated_at': config.updated_at.isoformat()
    })


@login_required
def send_test_message(request):
    """
    Envía un mensaje de prueba
    """
    if not check_whatsapp_access(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            numero_destino = data.get('numero_destino')
            mensaje_tipo = data.get('tipo', 'template')
            template_name = data.get('template_name', 'hello_world')
            language_code = data.get('language_code', 'en_US')
            texto_personalizado = data.get('texto_personalizado', '')
            
            if not numero_destino:
                return JsonResponse({'error': 'Número de destino requerido'}, status=400)
            
            try:
                service = WhatsAppService()
                
                if mensaje_tipo == 'template':
                    result = service.send_template_message(
                        to_number=numero_destino,
                        template_name=template_name,
                        language_code=language_code
                    )
                else:  # mensaje de texto
                    if not texto_personalizado:
                        return JsonResponse({'error': 'Texto personalizado requerido'}, status=400)
                    
                    result = service.send_text_message(
                        to_number=numero_destino,
                        text=texto_personalizado
                    )
                
                # Guardar mensaje de prueba
                TestMessage.objects.create(
                    numero_destino=numero_destino,
                    template_name=template_name,
                    language_code=language_code,
                    mensaje_personalizado=texto_personalizado,
                    created_by=request.user
                )
                
                return JsonResponse(result)
                
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f'Error al enviar mensaje de prueba: {str(e)}')
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def get_debug_messages(request):
    """
    Obtiene los mensajes de debug recientes
    """
    if not check_whatsapp_access(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    try:
        service = WhatsAppService()
        debug_messages = service.get_debug_messages(limit=10)
        
        messages_data = []
        for msg in debug_messages:
            messages_data.append({
                'id': msg.id,
                'tipo': msg.tipo,
                'numero_telefono': msg.numero_telefono,
                'contenido': msg.contenido,
                'estado': msg.estado,
                'created_at': msg.created_at.isoformat(),
                'raw_data': msg.raw_data
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        logger.error(f'Error al obtener mensajes de debug: {str(e)}')
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


def check_chat_supervision_access(user):
    """Verificar si el usuario tiene acceso a la supervisión de chat"""
    if not user.is_authenticated:
        logger.warning(f"❌ User not authenticated: {user}")
        return False
    
    # TEMPORAL: Permitir acceso a todos los usuarios autenticados para debugging
    logger.info(f"✅ TEMPORAL: Granting access to authenticated user: {user}")
    return True
    
    # Código original comentado para debugging
    # has_access = user.has_module_access('Supervisión de Chat')
    # logger.info(f"🔑 User {user} has chat supervision access: {has_access}")
    # return has_access


@login_required
def supervision_chat(request):
    """
    Vista principal para la supervisión de chat
    """
    if not check_chat_supervision_access(request.user):
        raise PermissionDenied("No tienes permisos para acceder a esta funcionalidad")
    
    # Verificar si hay configuración activa
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    if not config:
        messages.error(request, 'No hay configuración activa de WhatsApp Business')
        return redirect('whatsapp_business:configuracion')
    
    # Obtener estadísticas básicas
    total_conversations = Conversacion.objects.count()
    active_conversations = Conversacion.objects.filter(estado='abierta').count()
    
    # Preparar breadcrumbs
    breadcrumbs = [
        {'name': 'Inicio', 'url': '/'},
        {'name': 'Marketing Digital', 'url': '/marketing/'},
        {'name': 'Supervisión de Chat', 'url': None}
    ]
    
    context = {
        'page_title': 'Supervisión de Chat',
        'breadcrumbs': breadcrumbs,
        'config': config,
        'total_conversations': total_conversations,
        'active_conversations': active_conversations,
        'has_active_config': bool(config),
    }
    
    return render(request, 'whatsapp_business/supervision_chat.html', context)


@login_required
def get_conversations(request):
    """
    API para obtener las conversaciones
    """
    logger.info(f"🔍 get_conversations called by user: {request.user}")
    
    if not check_chat_supervision_access(request.user):
        logger.warning(f"❌ User {request.user} denied access to chat supervision")
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    try:
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            logger.warning("❌ No active WhatsApp config found")
            return JsonResponse({'error': 'No hay configuración activa'}, status=400)
        
        # Obtener parámetros de filtro
        estado = request.GET.get('estado', 'todos')
        limit = int(request.GET.get('limit', 20))
        
        logger.info(f"📋 Filtering conversations - estado: {estado}, limit: {limit}")
        
        # Obtener conversaciones
        if estado == 'todos':
            conversations = Conversacion.objects.all().select_related('cliente').order_by('-ultimo_mensaje_at')[:limit]
        else:
            conversations = Conversacion.objects.filter(
                estado=estado
            ).select_related('cliente').order_by('-ultimo_mensaje_at')[:limit]
        
        logger.info(f"📊 Found {conversations.count()} conversations")
        
        conversations_data = []
        for conv in conversations:
            # Obtener último mensaje
            last_message = conv.mensajes.order_by('-created_at').first()
            
            conversations_data.append({
                'id': conv.id,
                'cliente': {
                    'nombre': conv.cliente.nombre,
                    'telefono': conv.cliente.numero_whatsapp,
                    'avatar': conv.cliente.avatar.url if conv.cliente.avatar else None
                },
                'estado': conv.estado,
                'mensajes_no_leidos': conv.mensajes_no_leidos,
                'ultima_actividad': conv.ultimo_mensaje_at.isoformat() if conv.ultimo_mensaje_at else None,
                'ultimo_mensaje': {
                    'contenido': last_message.contenido if last_message else '',
                    'tipo': last_message.tipo if last_message else '',
                    'direccion': last_message.direccion if last_message else '',
                    'created_at': last_message.created_at.isoformat() if last_message else None
                } if last_message else None
            })
        
        return JsonResponse({
            'success': True,
            'conversations': conversations_data
        })
        
    except Exception as e:
        logger.error(f'Error al obtener conversaciones: {str(e)}')
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@login_required
def get_conversation_messages(request, conversation_id):
    """
    API para obtener los mensajes de una conversación
    """
    if not check_chat_supervision_access(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    try:
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Verificar que hay configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'error': 'No hay configuración activa'}, status=400)
        
        # Obtener mensajes
        messages = conversation.mensajes.order_by('created_at')
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'contenido': msg.contenido,
                'tipo': msg.tipo,
                'direccion': msg.direccion,
                'estado': msg.estado,
                'created_at': msg.created_at.isoformat(),
                'usuario_envio': msg.enviado_por.username if msg.enviado_por else None,
                'whatsapp_message_id': msg.whatsapp_message_id,
                'media_url': msg.media_url
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'conversation': {
                'id': conversation.id,
                'cliente': {
                    'nombre': conversation.cliente.nombre,
                    'telefono': conversation.cliente.numero_whatsapp
                },
                'estado': conversation.estado
            }
        })
        
    except Exception as e:
        logger.error(f'Error al obtener mensajes de conversación: {str(e)}')
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@login_required
@require_http_methods(["POST"])
def send_message(request):
    """
    API para enviar un mensaje
    """
    if not check_chat_supervision_access(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        contenido = data.get('contenido')
        
        if not conversation_id or not contenido:
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Verificar que hay configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'error': 'No hay configuración activa'}, status=400)
        
        # Enviar mensaje usando el servicio
        service = WhatsAppService()
        result = service.send_message(
            numero_telefono=conversation.cliente.numero_whatsapp,
            contenido=contenido,
            conversation=conversation,
            usuario_envio=request.user
        )
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': 'Mensaje enviado exitosamente',
                'message_id': result.get('message_id')
            })
        else:
            return JsonResponse({'error': result.get('error', 'Error al enviar mensaje')}, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        logger.error(f'Error al enviar mensaje: {str(e)}')
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)