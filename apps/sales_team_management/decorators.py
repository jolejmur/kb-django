"""
Decoradores personalizados para manejo de permisos con mensajes claros
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages
from .views.permission_views import permission_denied_view


def permission_required_with_message(permission, message=None):
    """
    Decorador que verifica permisos y muestra un mensaje personalizado
    cuando el usuario no tiene acceso.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(permission):
                # Mensaje personalizado por defecto
                if not message:
                    permission_name = permission.split('.')[-1].replace('_', ' ').title()
                    default_message = f"No tienes permisos para acceder a {permission_name}. Contacta al administrador para obtener los permisos necesarios."
                else:
                    default_message = message
                
                # Si es una petición AJAX, devolver JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': True,
                        'message': default_message,
                        'permission_required': permission
                    }, status=403)
                
                # Si es petición normal, usar la vista personalizada de error
                return permission_denied_view(request, permission_required=permission)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def team_management_permission_required(permission_type='view'):
    """
    Decorador específico para gestión de equipos con mensajes personalizados
    """
    permission_map = {
        'view': 'sales_team_management.view_organizationalunit',
        'add': 'sales_team_management.add_organizationalunit', 
        'change': 'sales_team_management.change_organizationalunit',
        'delete': 'sales_team_management.delete_organizationalunit',
        'view_members': 'sales_team_management.view_teammembership',
        'add_members': 'sales_team_management.add_teammembership',
        'change_members': 'sales_team_management.change_teammembership',
        'delete_members': 'sales_team_management.delete_teammembership',
        'view_hierarchy': 'sales_team_management.view_hierarchyrelation',
        'add_hierarchy': 'sales_team_management.add_hierarchyrelation',
        'view_commissions': 'sales_team_management.view_commissionstructure',
        'change_commissions': 'sales_team_management.change_commissionstructure'
    }
    
    message_map = {
        'view': 'No tienes permisos para ver la información de equipos.',
        'add': 'No tienes permisos para crear nuevos equipos.',
        'change': 'No tienes permisos para modificar equipos.',
        'delete': 'No tienes permisos para eliminar equipos.',
        'view_members': 'No tienes permisos para ver los miembros del equipo.',
        'add_members': 'No tienes permisos para agregar miembros al equipo.',
        'change_members': 'No tienes permisos para modificar miembros del equipo.',
        'delete_members': 'No tienes permisos para remover miembros del equipo.',
        'view_hierarchy': 'No tienes permisos para ver la jerarquía organizacional.',
        'add_hierarchy': 'No tienes permisos para crear relaciones jerárquicas.',
        'view_commissions': 'No tienes permisos para ver la configuración de comisiones.',
        'change_commissions': 'No tienes permisos para modificar las comisiones.'
    }
    
    permission = permission_map.get(permission_type)
    message = message_map.get(permission_type)
    
    if not permission:
        raise ValueError(f"Tipo de permiso no válido: {permission_type}")
    
    return permission_required_with_message(permission, message)