# apps/communications/consumers.py
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
        
        # Check if user has access to chat
        if not await self.has_chat_access():
            await self.close()
            return
        
        # Create user-specific group
        self.user_group_name = f'chat_user_{self.scope["user"].id}'
        
        # Join user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Also join general group for global messages
        self.general_group_name = 'whatsapp_messages'
        await self.channel_layer.group_add(
            self.general_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'WebSocket conectado. Recibirás mensajes en tiempo real.',
            'user_id': self.scope["user"].id,
            'user_group': self.user_group_name
        }))

    async def disconnect(self, close_code):
        # Leave groups
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        if hasattr(self, 'general_group_name'):
            await self.channel_layer.group_discard(
                self.general_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Handle incoming WebSocket messages (if needed)
        pass

    # Receive message from group
    async def whatsapp_message(self, event):
        message = event['message']
        
        # Check if this message is relevant for this user
        if await self.should_receive_message(message):
            # Send message to WebSocket
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message': message
            }))

    @database_sync_to_async
    def has_chat_access(self):
        """Check if user has chat access"""
        user = self.scope["user"]
        if not user.is_authenticated:
            return False
        
        # Check if user has access to chat vendedor or supervision chat
        return (
            user.is_superuser or
            user.has_module_access('Chat Vendedor') or
            user.has_module_access('Supervisión de Chat') or
            user.has_module_access('Configuración Meta Business')
        )
    
    @database_sync_to_async
    def should_receive_message(self, message):
        """Check if user should receive this specific message"""
        user = self.scope["user"]
        
        # Superusers receive all messages
        if user.is_superuser:
            return True
            
        # Check if user has access to this conversation
        if message.get('numero_telefono'):
            from apps.sales_team_management.models import TeamMembership
            from apps.communications.models import LeadAssignment
            
            try:
                # Get user's team membership
                user_membership = TeamMembership.objects.filter(
                    user=user,
                    status='ACTIVE'
                ).select_related('organizational_unit').first()
                
                if user_membership:
                    # Check if user's team has access to this conversation
                    team_assignments = LeadAssignment.objects.filter(
                        organizational_unit=user_membership.organizational_unit,
                        is_active=True,
                        lead__cliente__numero_whatsapp=message['numero_telefono']
                    )
                    return team_assignments.exists()
                    
            except Exception as e:
                print(f"Error checking message access: {e}")
                return False
                
        return False


class ChatVendedorConsumer(WhatsAppMessageConsumer):
    """Consumer específico para chat de vendedor"""
    
    async def connect(self):
        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        # Check if user has access to chat vendedor specifically
        if not await self.has_vendedor_chat_access():
            await self.close()
            return
        
        # Create user-specific group
        self.user_group_name = f'chat_vendedor_{self.scope["user"].id}'
        
        # Join user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Chat vendedor conectado',
            'user_id': self.scope["user"].id
        }))
    
    @database_sync_to_async
    def has_vendedor_chat_access(self):
        """Check if user has vendedor chat access"""
        user = self.scope["user"]
        if not user.is_authenticated:
            return False
        
        # Only allow users with specific chat access
        return (
            user.is_superuser or
            user.has_module_access('Chat Vendedor')
        )


class SupervisionChatConsumer(WhatsAppMessageConsumer):
    """Consumer específico para supervisión de chat"""
    
    async def connect(self):
        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        # Check if user has access to supervision chat specifically
        if not await self.has_supervision_chat_access():
            await self.close()
            return
        
        # Create user-specific group
        self.user_group_name = f'supervision_chat_{self.scope["user"].id}'
        
        # Join user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial message
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Supervisión de chat conectado',
            'user_id': self.scope["user"].id
        }))
    
    @database_sync_to_async
    def has_supervision_chat_access(self):
        """Check if user has supervision chat access"""
        user = self.scope["user"]
        if not user.is_authenticated:
            return False
        
        # Only allow users with supervision access
        return (
            user.is_superuser or
            user.has_module_access('Supervisión de Chat')
        )