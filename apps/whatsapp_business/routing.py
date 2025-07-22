# apps/whatsapp_business/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/whatsapp/messages/$', consumers.WhatsAppMessageConsumer.as_asgi()),
]