# apps/whatsapp_business/urls.py
from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    # Panel principal de Gestión de Leads (nueva URL mejorada)
    path('lead-management/', views.lead_management_dashboard, name='lead_management_dashboard'),
    
    # Dashboard ejecutivo de insights de leads
    path('lead-insights/', views.lead_insights_dashboard, name='lead_insights_dashboard'),
    
    # Página principal redirige al dashboard de gestión
    path('', views.lead_management_dashboard, name='leads_list'),
    
    # Configuración de WhatsApp Business
    path('configuracion/', views.configuracion_whatsapp, name='configuracion'),
    
    # Chat para vendedores (solo sus leads asignados)
    path('chat/', views.chat_vendedor, name='chat_vendedor'),
    
    # Supervisión de Chat para jefes/team leaders
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
    
    # API para chat de vendedores
    path('api/chat/conversations/', views.get_vendedor_conversations, name='get_vendedor_conversations'),
    path('api/chat/conversation/<int:conversation_id>/messages/', views.get_vendedor_conversation_messages, name='get_vendedor_conversation_messages'),
    path('api/chat/send-message/', views.send_vendedor_message, name='send_vendedor_message'),
    path('api/chat/send-media/', views.send_vendedor_media, name='send_vendedor_media'),
    path('api/chat/mark-read/', views.mark_vendedor_conversation_read, name='mark_vendedor_conversation_read'),
    
    # API para supervision-chat (idénticas pero con filtros jerárquicos)
    path('api/supervision-chat/conversations/', views.get_supervision_conversations, name='get_supervision_conversations'),
    path('api/supervision-chat/conversation/<int:conversation_id>/messages/', views.get_supervision_conversation_messages, name='get_supervision_conversation_messages'),
    path('api/supervision-chat/send-message/', views.send_supervision_message, name='send_supervision_message'),
    path('api/supervision-chat/send-media/', views.send_supervision_media, name='send_supervision_media'),
    path('api/supervision-chat/mark-read/', views.mark_supervision_conversation_read, name='mark_supervision_conversation_read'),
    path('api/chat/audio/<int:message_id>/', views.serve_audio_converted, name='serve_audio_converted'),
    path('api/chat/audio-debug/<int:message_id>/', views.test_audio_debug, name='test_audio_debug'),
    
    # Distribución de Leads
    path('lead-distribution/', views.lead_distribution_config, name='lead_distribution_config'),
    path('lead-distribution/history/', views.lead_assignments_history, name='lead_assignments_history'),
    path('lead-distribution/manual/', views.manual_lead_assignment, name='manual_lead_assignment'),
    path('api/lead-distribution/update/', views.update_lead_distribution, name='update_lead_distribution'),
    path('api/lead-distribution/assign/', views.assign_lead_to_salesperson, name='assign_lead_to_salesperson'),
    path('api/sales-team/<int:unit_id>/members/', views.get_sales_team_members, name='get_sales_team_members'),
    path('api/lead/<int:lead_id>/reject/', views.reject_lead, name='reject_lead'),
    
    # Mobile API endpoints for Flutter app
    path('api/mobile/chats/', views.get_chats, name='mobile_get_chats'),
    path('api/mobile/chat/<int:chat_id>/messages/', views.get_messages, name='mobile_get_messages'),
    path('api/mobile/chat/<int:chat_id>/send/', views.send_message_mobile, name='mobile_send_message'),
]

