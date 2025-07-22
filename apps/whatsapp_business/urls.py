# apps/whatsapp_business/urls.py
from django.urls import path
from . import views

app_name = 'whatsapp_business'

urlpatterns = [
    # Página principal de leads
    path('', views.leads_list, name='leads_list'),
    
    # Configuración de WhatsApp Business
    path('configuracion/', views.configuracion_whatsapp, name='configuracion'),
    
    # Supervisión de Chat
    path('supervision-chat/', views.supervision_chat, name='supervision_chat'),
    
    # Acciones para configuraciones
    path('configuracion/<int:config_id>/activar/', views.activar_configuracion, name='activar_configuracion'),
    path('configuracion/<int:config_id>/eliminar/', views.eliminar_configuracion, name='eliminar_configuracion'),
    
    # Pruebas
    path('test-webhook/', views.test_webhook, name='test_webhook'),
    
    # Webhook de WhatsApp
    path('webhook/', views.webhook_whatsapp, name='webhook'),
    
    # API de estado
    path('api/status/', views.status_api, name='status_api'),
    
    # API para enviar mensajes de prueba
    path('api/send-test-message/', views.send_test_message, name='send_test_message'),
    
    # API para obtener mensajes de debug
    path('api/debug-messages/', views.get_debug_messages, name='get_debug_messages'),
    
    # API para supervisión de chat
    path('api/conversations/', views.get_conversations, name='get_conversations'),
    path('api/conversation/<int:conversation_id>/messages/', views.get_conversation_messages, name='get_conversation_messages'),
    path('api/send-message/', views.send_message, name='send_message'),
]