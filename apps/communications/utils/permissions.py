# apps/communications/utils/permissions.py
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def check_whatsapp_access(user):
    """
    Verifica si el usuario tiene acceso a configuración de WhatsApp
    """
    if not user.is_authenticated:
        return False
    
    # Solo superusuarios pueden acceder a configuración
    if user.is_superuser:
        return True
    
    # Verificar permisos específicos del módulo
    if hasattr(user, 'has_module_access'):
        return user.has_module_access('whatsapp_business')
    
    return False


def check_chat_supervision_access(user):
    """
    Verifica acceso a supervisión de chat
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Verificar si es gerente general o gerente comercial (sin equipo específico)
    from apps.sales_team_management.models import TeamMembership
    user_membership = TeamMembership.objects.filter(
        user=user,
        is_active=True
    ).select_related('position_type').first()
    
    if not user_membership:
        # Usuario sin equipo específico - permitir acceso (gerente general, etc.)
        return True
    
    # Verificar si es gerente de equipo (por position_type)
    if user_membership.position_type and 'gerente' in user_membership.position_type.name.lower():
        return True
    
    # Verificar si tiene subalternos (es supervisor)
    from apps.sales_team_management.models import HierarchyRelation
    has_subordinates = HierarchyRelation.objects.filter(
        supervisor_membership__user=user,
        is_active=True
    ).exists()
    
    if has_subordinates:
        return True
    
    # Verificar permisos específicos del módulo
    if hasattr(user, 'has_module_access'):
        return user.has_module_access('chat_supervision')
    
    return False


def check_chat_vendedor_access(user):
    """
    Verifica acceso a chat de vendedor
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Verificar si es miembro de equipo de ventas
    from apps.sales_team_management.models import TeamMembership
    user_membership = TeamMembership.objects.filter(
        user=user,
        is_active=True
    ).exists()
    
    if user_membership:
        return True
    
    # Permitir acceso a usuarios sin equipo (gerentes generales, etc.)
    # Aunque solo verán chats asignados específicamente a ellos
    if not user_membership:
        return True
    
    # Verificar permisos específicos del módulo
    if hasattr(user, 'has_module_access'):
        return user.has_module_access('chat_vendedor')
    
    return False


def check_lead_management_access(user):
    """
    Verifica acceso a gestión de leads
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Verificar si es gerente general o gerente comercial (sin equipo específico)
    from apps.sales_team_management.models import TeamMembership
    user_membership = TeamMembership.objects.filter(
        user=user,
        is_active=True
    ).select_related('position_type').first()
    
    if not user_membership:
        # Usuario sin equipo específico - permitir acceso (gerente general, etc.)
        return True
    
    # Verificar si es gerente de equipo (por position_type)
    if user_membership.position_type and 'gerente' in user_membership.position_type.name.lower():
        return True
    
    # Verificar si tiene subalternos (es supervisor)
    from apps.sales_team_management.models import HierarchyRelation
    has_subordinates = HierarchyRelation.objects.filter(
        supervisor_membership__user=user,
        is_active=True
    ).exists()
    
    if has_subordinates:
        return True
    
    # Verificar permisos específicos del módulo
    if hasattr(user, 'has_module_access'):
        return user.has_module_access('lead_management')
    
    return False


def require_whatsapp_access(view_func):
    """
    Decorador que requiere acceso a WhatsApp
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_whatsapp_access(request.user):
            raise PermissionDenied("No tienes permisos para acceder a la configuración de WhatsApp")
        return view_func(request, *args, **kwargs)
    return wrapper


def require_chat_supervision_access(view_func):
    """
    Decorador que requiere acceso a supervisión de chat
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_chat_supervision_access(request.user):
            raise PermissionDenied("No tienes permisos para acceder a la supervisión de chat")
        return view_func(request, *args, **kwargs)
    return wrapper


def require_chat_vendedor_access(view_func):
    """
    Decorador que requiere acceso a chat de vendedor
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_chat_vendedor_access(request.user):
            raise PermissionDenied("No tienes permisos para acceder al chat de vendedor")
        return view_func(request, *args, **kwargs)
    return wrapper


def require_lead_management_access(view_func):
    """
    Decorador que requiere acceso a gestión de leads
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_lead_management_access(request.user):
            raise PermissionDenied("No tienes permisos para acceder a la gestión de leads")
        return view_func(request, *args, **kwargs)
    return wrapper


def api_require_whatsapp_access(view_func):
    """
    Decorador API que requiere acceso a WhatsApp
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_whatsapp_access(request.user):
            return JsonResponse({'error': 'Sin permisos para acceder a WhatsApp'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def api_require_chat_supervision_access(view_func):
    """
    Decorador API que requiere acceso a supervisión de chat
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_chat_supervision_access(request.user):
            return JsonResponse({'error': 'Sin permisos para acceder a supervisión de chat'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def api_require_chat_vendedor_access(view_func):
    """
    Decorador API que requiere acceso a chat de vendedor
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_chat_vendedor_access(request.user):
            return JsonResponse({'error': 'Sin permisos para acceder al chat'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def api_require_lead_management_access(view_func):
    """
    Decorador API que requiere acceso a gestión de leads
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not check_lead_management_access(request.user):
            return JsonResponse({'error': 'Sin permisos para acceder a gestión de leads'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper