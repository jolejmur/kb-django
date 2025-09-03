# apps/communications/views/webhook_handlers.py
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..models import WhatsAppConfig, WebhookDebugMessage
from ..services.message_service import MessageService
from .. import services
from ..utils.permissions import api_require_whatsapp_access
from ..utils.formatters import ResponseFormatter
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook_whatsapp(request):
    """
    Webhook para recibir mensajes de WhatsApp Business
    """
    if request.method == 'GET':
        # Verificación del webhook
        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        mode = request.GET.get('hub.mode')
        
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
            
            # Guardar datos para debug
            try:
                WebhookDebugMessage.objects.create(
                    raw_data=data,
                    status='received'
                )
            except Exception as debug_error:
                logger.warning(f'Error guardando debug: {debug_error}')
            
            # Procesar mensajes usando el servicio
            success, message = MessageService.process_incoming_webhook_message(data)
            
            if success:
                return JsonResponse({'status': 'success'}, status=200)
            else:
                logger.error(f'Error procesando webhook: {message}')
                return JsonResponse({'error': message}, status=500)
                
        except json.JSONDecodeError:
            logger.error('Error al decodificar JSON del webhook')
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f'Error al procesar webhook: {str(e)}')
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
@api_require_whatsapp_access
def status_api(request):
    """
    API para obtener el estado de la configuración de WhatsApp
    """
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    
    if not config:
        return ResponseFormatter.success_response({
            'status': 'no_config',
            'message': 'No hay configuración activa'
        })
    
    return ResponseFormatter.success_response({
        'status': 'active',
        'phone_number_id': config.phone_number_id,
        'business_account_id': config.business_account_id,
        'webhook_url': config.webhook_url,
        'created_at': config.created_at.isoformat(),
        'updated_at': config.updated_at.isoformat()
    })


@login_required
@require_http_methods(["POST"])
@api_require_whatsapp_access
def send_test_message(request):
    """
    Envía un mensaje de prueba (template hello_world)
    """
    try:
        data = json.loads(request.body)
        # El template envía 'numero_destino', no 'numero_telefono'
        numero_telefono = data.get('numero_destino') or data.get('numero_telefono')
        tipo = data.get('tipo', 'template')
        template_name = data.get('template_name', 'hello_world')
        
        if not numero_telefono:
            return ResponseFormatter.error_response('Número de teléfono es requerido', 400)
        
        # Verificar configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            return ResponseFormatter.error_response('No hay configuración activa', 400)
        
        # Enviar mensaje de template usando requests directamente
        import requests
        api_url = "https://graph.facebook.com/v22.0"
        headers = {
            'Authorization': f'Bearer {config.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Datos para mensaje de template hello_world
        data_payload = {
            'messaging_product': 'whatsapp',
            'to': numero_telefono,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {
                    'code': 'en_US'
                }
            }
        }
        
        response = requests.post(
            f'{api_url}/{config.phone_number_id}/messages',
            json=data_payload,
            headers=headers
        )
        
        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get('messages', [{}])[0].get('id')
            
            # Crear mensaje de debug
            debug_message = WebhookDebugMessage.objects.create(
                tipo='test_message',
                numero_telefono=numero_telefono,
                contenido=f'Template: {template_name}',
                raw_data=response_data,
                estado='enviado',
                config_utilizada=config
            )
            
            return ResponseFormatter.success_response({
                'message_id': message_id,
                'debug_message_id': debug_message.id
            }, 'Mensaje de prueba enviado exitosamente')
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {'error': response.text}
            
            # Crear mensaje de debug con error
            WebhookDebugMessage.objects.create(
                tipo='test_message',
                numero_telefono=numero_telefono,
                contenido=f'Error: Template {template_name}',
                raw_data=error_data,
                estado='error',
                config_utilizada=config
            )
            
            return ResponseFormatter.error_response(f'Error enviando mensaje: {error_data}', 500)
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error enviando mensaje de prueba: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@api_require_whatsapp_access
def get_debug_messages(request):
    """
    API para obtener los últimos 10 mensajes de debug del webhook
    """
    try:
        # Solo los últimos 10 mensajes para historial en tiempo real
        limit = int(request.GET.get('limit', 10))
        limit = min(limit, 20)  # Máximo 20 mensajes
        
        # Obtener mensajes directamente sin filtros complejos
        messages = WebhookDebugMessage.objects.order_by('-created_at')[:limit]
        
        # Formatear datos
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'tipo': msg.tipo,
                'numero_telefono': msg.numero_telefono,
                'contenido': msg.contenido,
                'estado': msg.estado,
                'created_at': msg.created_at.isoformat()
            })
        
        return ResponseFormatter.success_response({
            'messages': messages_data,
            'total': len(messages_data)
        })
        
    except Exception as e:
        logger.error(f'Error obteniendo mensajes de debug: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@require_http_methods(["POST"])
@api_require_whatsapp_access
def test_webhook(request):
    """
    API para probar el webhook manualmente
    """
    try:
        data = json.loads(request.body)
        
        # Simular un webhook de WhatsApp
        webhook_data = data.get('webhook_data')
        if not webhook_data:
            return ResponseFormatter.error_response('Datos de webhook requeridos', 400)
        
        # Procesar usando el servicio
        success, message = MessageService.process_incoming_webhook_message(webhook_data)
        
        if success:
            return ResponseFormatter.success_response({
                'processed': True,
                'message': message
            }, 'Webhook procesado exitosamente')
        else:
            return ResponseFormatter.error_response(message, 400)
        
    except json.JSONDecodeError:
        return ResponseFormatter.error_response('Datos JSON inválidos', 400)
    except Exception as e:
        logger.error(f'Error probando webhook: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)