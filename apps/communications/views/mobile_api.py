# apps/communications/views/mobile_api.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["GET"])
def get_chats(request):
    """API endpoint para obtener chats - Mobile Flutter app"""
    return JsonResponse({
        'status': 'success',
        'chats': []
    })

@csrf_exempt  
@require_http_methods(["GET"])
def get_messages(request, chat_id):
    """API endpoint para obtener mensajes de un chat - Mobile Flutter app"""
    return JsonResponse({
        'status': 'success',
        'messages': []
    })

@csrf_exempt
@require_http_methods(["POST"])
def send_message_mobile(request, chat_id):
    """API endpoint para enviar mensaje - Mobile Flutter app"""
    return JsonResponse({
        'status': 'success',
        'message': 'Message sent'
    })