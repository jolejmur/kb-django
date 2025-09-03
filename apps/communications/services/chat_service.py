# apps/communications/services/chat_service.py
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from ..models import Conversacion, Mensaje, WhatsAppConfig, Lead, LeadAssignment
from apps.sales_team_management.models import TeamMembership
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """
    Servicio para manejar la lógica de negocio del chat
    """
    
    @staticmethod
    def get_user_accessible_leads_for_chat(user):
        """
        Para CHAT VENDEDOR: Solo leads asignados específicamente al usuario
        """
        # SIEMPRE solo leads asignados al usuario específico, sin importar rol
        user_assignments = LeadAssignment.objects.filter(
            assigned_to_user=user,
            is_active=True
        ).select_related('lead__cliente')
        return [assignment.lead for assignment in user_assignments]
    
    @staticmethod
    def get_user_accessible_leads_for_supervision(user):
        """
        Para SUPERVISIÓN: Leads de subalternos + todos si no tiene equipo
        """
        from apps.sales_team_management.models import HierarchyRelation
        
        # Verificar si el usuario tiene equipo
        user_membership = TeamMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('organizational_unit').first()
        
        if not user_membership:
            # Usuario sin equipo (admin, gerente comercial) - TODOS los leads
            return Lead.objects.filter(is_active=True).select_related('cliente')
        
        # Usuario con equipo - verificar si es gerente del equipo completo
        subordinate_users = set()
        
        # Verificar si es gerente/líder del equipo (puede ver todo el equipo)
        if user_membership.position_type and user_membership.position_type.name in ['Gerente de Equipo', 'Team Manager']:
            # Gerente de equipo: puede ver TODOS los miembros de su equipo
            all_team_members = TeamMembership.objects.filter(
                organizational_unit=user_membership.organizational_unit,
                is_active=True
            ).values_list('user', flat=True)
            subordinate_users.update(all_team_members)
        else:
            # Lógica normal de supervisión jerárquica
            # 1. Supervisión directa
            direct_subordinates = HierarchyRelation.objects.filter(
                supervisor_membership__user=user,
                is_active=True,
                relation_type='DIRECT_SUPERVISION'
            ).values_list('subordinate_membership__user', flat=True)
            subordinate_users.update(direct_subordinates)
            
            # 2. Supervisión rígida (jerárquica)
            hierarchical_subordinates = HierarchyRelation.objects.filter(
                supervisor_membership__user=user,
                is_active=True,
                relation_type='HIERARCHICAL'
            ).values_list('subordinate_membership__user', flat=True)
            subordinate_users.update(hierarchical_subordinates)
            
            # 3. Incluir al propio usuario (puede ver sus propios chats también)
            subordinate_users.add(user.id)
        
        # Obtener leads asignados a todos los subalternos
        subordinate_assignments = LeadAssignment.objects.filter(
            assigned_to_user_id__in=subordinate_users,
            is_active=True
        ).select_related('lead__cliente')
        
        return [assignment.lead for assignment in subordinate_assignments]
    
    @staticmethod
    def get_user_accessible_leads(user):
        """
        Método legacy - mantener para compatibilidad
        """
        return ChatService.get_user_accessible_leads_for_chat(user)
    
    @staticmethod
    def get_conversations_for_user(user):
        """
        Método legacy - obtiene conversaciones para chat vendedor
        """
        return ChatService.get_conversations_for_chat(user)
    
    @staticmethod
    def get_conversations_for_chat(user):
        """
        Para CHAT VENDEDOR: Solo conversaciones de leads asignados al usuario
        """
        # Verificar configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            return [], "No hay configuración activa"
        
        # Obtener leads asignados específicamente al usuario
        accessible_leads = ChatService.get_user_accessible_leads_for_chat(user)
        lead_phone_numbers = [lead.cliente.numero_whatsapp for lead in accessible_leads]
        
        # Obtener conversaciones
        conversations = Conversacion.objects.filter(
            numero_whatsapp__in=lead_phone_numbers,
            is_active=True
        ).select_related('cliente').order_by('-ultimo_mensaje_at')
        
        return conversations, None
    
    @staticmethod
    def get_conversations_for_supervision(user):
        """
        Para SUPERVISIÓN: Conversaciones de subalternos + todas si no tiene equipo
        """
        # Verificar configuración activa
        config = WhatsAppConfig.objects.filter(is_active=True).first()
        if not config:
            return [], "No hay configuración activa"
        
        # Obtener leads accesibles para supervisión
        accessible_leads = ChatService.get_user_accessible_leads_for_supervision(user)
        lead_phone_numbers = [lead.cliente.numero_whatsapp for lead in accessible_leads]
        
        # Obtener conversaciones
        conversations = Conversacion.objects.filter(
            numero_whatsapp__in=lead_phone_numbers,
            is_active=True
        ).select_related('cliente').order_by('-ultimo_mensaje_at')
        
        return conversations, None
    
    @staticmethod
    def build_conversation_data(conversation):
        """
        Construye datos estructurados de una conversación
        """
        last_message = conversation.mensajes.order_by('-created_at').first()
        
        # Último mensaje entrante para verificar 24h
        last_incoming_message = conversation.mensajes.filter(
            direccion='incoming'
        ).order_by('-created_at').first()
        
        # Buscar asignación del lead (lo hacemos primero para reutilizar)
        lead_assignment = None
        try:
            lead_assignment = LeadAssignment.objects.filter(
                lead__cliente__numero_whatsapp=conversation.numero_whatsapp,
                is_active=True
            ).select_related('assigned_to_user', 'organizational_unit').first()
        except:
            pass
        
        # Verificar si el vendedor ha respondido después de la asignación
        has_vendedor_response = False
        has_ever_responded = False
        if lead_assignment and lead_assignment.assigned_to_user:
            # Respuesta después de asignación (para hora A)
            vendedor_responses = conversation.mensajes.filter(
                direccion='outgoing',
                enviado_por=lead_assignment.assigned_to_user,
                created_at__gte=lead_assignment.assigned_date
            )
            has_vendedor_response = vendedor_responses.exists()
            
            # Respuesta alguna vez (para determinar color de vencimiento)
            ever_responded = conversation.mensajes.filter(
                direccion='outgoing',
                enviado_por=lead_assignment.assigned_to_user
            )
            has_ever_responded = ever_responded.exists()
        
        # Verificar respuesta después del último mensaje entrante
        has_response_after_incoming = False
        is_expired = False
        
        if last_incoming_message:
            try:
                # Si hay un vendedor asignado específicamente, verificar solo sus respuestas
                if lead_assignment and lead_assignment.assigned_to_user:
                    response_after_incoming = conversation.mensajes.filter(
                        direccion='outgoing',
                        created_at__gt=last_incoming_message.created_at,
                        enviado_por=lead_assignment.assigned_to_user
                    ).exists()
                else:
                    # Si no hay vendedor específico asignado, verificar cualquier respuesta
                    response_after_incoming = conversation.mensajes.filter(
                        direccion='outgoing',
                        created_at__gt=last_incoming_message.created_at
                    ).exists()
                
                has_response_after_incoming = response_after_incoming
                
                # Verificar si han pasado 24 horas sin respuesta DEL VENDEDOR ASIGNADO
                if not has_response_after_incoming:
                    hours_since_incoming = (timezone.now() - last_incoming_message.created_at).total_seconds() / 3600
                    is_expired = hours_since_incoming > 24
            except:
                # Fallback: usar lógica original si hay error
                response_after_incoming = conversation.mensajes.filter(
                    direccion='outgoing',
                    created_at__gt=last_incoming_message.created_at
                ).exists()
                
                has_response_after_incoming = response_after_incoming
                
                if not has_response_after_incoming:
                    hours_since_incoming = (timezone.now() - last_incoming_message.created_at).total_seconds() / 3600
                    is_expired = hours_since_incoming > 24
        
        # Información del vendedor asignado y equipo
        assigned_salesperson = None
        team_info = None
        
        if lead_assignment:
            # Información del equipo siempre disponible si hay asignación
            if lead_assignment.organizational_unit:
                team_info = {
                    'name': lead_assignment.organizational_unit.name,
                    'id': lead_assignment.organizational_unit.id
                }
            
            # Información del vendedor si está asignado específicamente
            if lead_assignment.assigned_to_user:
                assigned_salesperson = {
                    'name': lead_assignment.assigned_to_user.get_full_name(),
                    'username': lead_assignment.assigned_to_user.username
                }
        
        # URL para gestión de leads si no está asignado
        lead_management_url = None
        if not assigned_salesperson:
            lead_management_url = '/marketing/lead-management/'
        
        return {
            'id': conversation.id,
            'cliente_nombre': conversation.cliente.nombre_completo,
            'numero_whatsapp': conversation.numero_whatsapp,
            'estado': conversation.estado,
            'mensajes_no_leidos': conversation.mensajes_no_leidos,
            'ultimo_mensaje_at': conversation.ultimo_mensaje_at.isoformat() if conversation.ultimo_mensaje_at else None,
            'ultimo_mensaje_contenido': last_message.contenido if last_message else '',
            'ultimo_mensaje_preview': last_message.contenido[:50] + '...' if last_message and len(last_message.contenido) > 50 else (last_message.contenido if last_message else ''),
            'ultimo_mensaje_tipo': last_message.direccion if last_message else 'incoming',
            'assigned_salesperson': assigned_salesperson,
            'team_info': team_info,
            'has_assignment': lead_assignment is not None,
            'assignment_status': 'assigned' if assigned_salesperson else ('team_only' if lead_assignment else 'unassigned'),
            'lead_management_url': lead_management_url,
            'is_expired': is_expired,
            'has_unanswered_message': last_incoming_message and not has_response_after_incoming,
            'last_incoming_at': last_incoming_message.created_at.isoformat() if last_incoming_message else None,
            # Nuevos campos para las horas especiales
            'assignment_date': lead_assignment.assigned_date.isoformat() if lead_assignment else None,
            'has_vendedor_response': has_vendedor_response,
            'has_ever_responded': has_ever_responded
        }
    
    @staticmethod
    def user_has_conversation_access_for_chat(user, conversation):
        """
        Para CHAT VENDEDOR: Verifica si el usuario tiene acceso específico a la conversación
        """
        # SIEMPRE verificar asignación específica, sin importar si es admin
        user_assignments = LeadAssignment.objects.filter(
            assigned_to_user=user,
            is_active=True,
            lead__cliente__numero_whatsapp=conversation.numero_whatsapp
        )
        return user_assignments.exists()
    
    @staticmethod
    def user_has_conversation_access_for_supervision(user, conversation):
        """
        Para SUPERVISIÓN: Verifica acceso basado en jerarquía o si no tiene equipo
        """
        from apps.sales_team_management.models import HierarchyRelation
        
        # Verificar si el usuario tiene equipo
        user_membership = TeamMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('organizational_unit').first()
        
        if not user_membership:
            # Usuario sin equipo (admin, gerente comercial) - acceso completo
            return True
        
        # Obtener el lead asociado a la conversación
        try:
            lead = Lead.objects.get(
                cliente__numero_whatsapp=conversation.numero_whatsapp,
                is_active=True
            )
            assignment = lead.assignments.filter(is_active=True).first()
            
            if not assignment or not assignment.assigned_to_user:
                return False
            
            assigned_user = assignment.assigned_to_user
            
            # Verificar si es el propio usuario
            if assigned_user.id == user.id:
                return True
            
            # Verificar si es gerente del equipo (puede acceder a todos los miembros de su equipo)
            if user_membership.position_type and user_membership.position_type.name in ['Gerente de Equipo', 'Team Manager']:
                # Verificar si el usuario asignado pertenece al mismo equipo
                assigned_user_membership = TeamMembership.objects.filter(
                    user=assigned_user,
                    organizational_unit=user_membership.organizational_unit,
                    is_active=True
                ).exists()
                
                if assigned_user_membership:
                    return True
            
            # Verificar si supervisa directamente al usuario asignado
            direct_supervision = HierarchyRelation.objects.filter(
                supervisor_membership__user=user,
                subordinate_membership__user=assigned_user,
                is_active=True,
                relation_type='DIRECT_SUPERVISION'
            ).exists()
            
            if direct_supervision:
                return True
            
            # Verificar supervisión jerárquica
            hierarchical_supervision = HierarchyRelation.objects.filter(
                supervisor_membership__user=user,
                subordinate_membership__user=assigned_user,
                is_active=True,
                relation_type='HIERARCHICAL'
            ).exists()
            
            return hierarchical_supervision
            
        except Lead.DoesNotExist:
            return False
    
    @staticmethod
    def user_has_conversation_access(user, conversation):
        """
        Método legacy - usar para chat vendedor por defecto
        """
        return ChatService.user_has_conversation_access_for_chat(user, conversation)
    
    @staticmethod
    def get_conversation_messages(conversation_id, user):
        """
        Obtiene mensajes de una conversación verificando acceso (para chat vendedor)
        """
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Verificar acceso usando método para chat vendedor
        if not ChatService.user_has_conversation_access_for_chat(user, conversation):
            return None, "No tienes acceso a esta conversación"
        
        # Obtener mensajes
        messages = conversation.mensajes.order_by('created_at')
        
        messages_data = []
        for msg in messages:
            message_data = {
                'id': msg.id,
                'contenido': msg.contenido,
                'tipo': msg.tipo,
                'direccion': msg.direccion,
                'estado': msg.estado,
                'timestamp_whatsapp': msg.timestamp_whatsapp.isoformat() if msg.timestamp_whatsapp else None,
                'created_at': msg.created_at.isoformat(),
                'enviado_por': msg.enviado_por.get_full_name() if msg.enviado_por else None,
                'media_url': msg.media_url if msg.media_url else None,
                'archivo_local': msg.archivo_local.url if msg.archivo_local else None,
                'archivo_tipo_mime': msg.archivo_tipo_mime,
                'archivo_nombre': msg.archivo_nombre,
                'archivo_tamaño': msg.archivo_tamaño,
                'caption': getattr(msg, 'caption', None)
            }
            messages_data.append(message_data)
        
        # Marcar como leídos
        conversation.mensajes_no_leidos = 0
        conversation.save()
        
        return {
            'conversation': {
                'id': conversation.id,
                'cliente_nombre': conversation.cliente.nombre_completo,
                'numero_whatsapp': conversation.numero_whatsapp,
                'estado': conversation.estado
            },
            'messages': messages_data
        }, None

    @staticmethod
    def get_conversation_messages_for_supervision(conversation_id, user):
        """
        Obtiene mensajes de una conversación verificando acceso (para supervisión)
        """
        conversation = get_object_or_404(Conversacion, id=conversation_id)
        
        # Verificar acceso usando método para supervisión
        if not ChatService.user_has_conversation_access_for_supervision(user, conversation):
            return None, "No tienes acceso a esta conversación"
        
        # Obtener mensajes
        messages = conversation.mensajes.order_by('created_at')
        
        messages_data = []
        for msg in messages:
            message_data = {
                'id': msg.id,
                'contenido': msg.contenido,
                'tipo': msg.tipo,
                'direccion': msg.direccion,
                'estado': msg.estado,
                'timestamp_whatsapp': msg.timestamp_whatsapp.isoformat() if msg.timestamp_whatsapp else None,
                'created_at': msg.created_at.isoformat(),
                'enviado_por': msg.enviado_por.get_full_name() if msg.enviado_por else None,
                'media_url': msg.media_url if msg.media_url else None,
                'archivo_local': msg.archivo_local.url if msg.archivo_local else None,
                'archivo_tipo_mime': msg.archivo_tipo_mime,
                'archivo_nombre': msg.archivo_nombre,
                'archivo_tamaño': msg.archivo_tamaño,
                'caption': getattr(msg, 'caption', None)
            }
            messages_data.append(message_data)
        
        # Marcar como leídos
        conversation.mensajes_no_leidos = 0
        conversation.save()
        
        return {
            'conversation': {
                'id': conversation.id,
                'cliente_nombre': conversation.cliente.nombre_completo,
                'numero_whatsapp': conversation.numero_whatsapp,
                'estado': conversation.estado
            },
            'messages': messages_data
        }, None