# apps/whatsapp_business/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/whatsapp/messages/$', consumers.WhatsAppMessageConsumer.as_asgi()),
    re_path(r'ws/chat-vendedor/$', consumers.ChatVendedorConsumer.as_asgi()),
    re_path(r'ws/supervision-chat/$', consumers.SupervisionChatConsumer.as_asgi()),
]