# apps/whatsapp_business/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import WhatsAppConfig

class WhatsAppMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        # Check if user has access to WhatsApp Business
        if not await self.has_whatsapp_access():
            await self.close()
            return
        
        self.group_name = 'whatsapp_messages'
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'WebSocket conectado. Recibirás mensajes en tiempo real.'
        }))

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle incoming WebSocket messages (if needed)
        pass

    # Receive message from group
    async def whatsapp_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    @database_sync_to_async
    def has_whatsapp_access(self):
        """Check if user has WhatsApp access"""
        user = self.scope["user"]
        if not user.is_authenticated:
            return False
        return user.has_module_access('Configuración Meta Business')