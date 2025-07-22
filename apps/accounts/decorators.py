"""
Decorators for role-based permission handling
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Decorator that checks if user has any of the allowed roles
    Usage: @role_required('Ventas', 'Registro', 'Super Admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.role:
                messages.error(request, 'No tienes un rol asignado. Contacta al administrador.')
                return redirect('core:dashboard')
            
            if request.user.role.name not in allowed_roles:
                messages.error(request, 'No tienes permisos para acceder a esta sección.')
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def module_required(module_name):
    """
    Decorator that checks if user has access to a specific module
    Usage: @module_required('Gestión de Equipos')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.has_module_access(module_name):
                messages.error(request, f'No tienes acceso al módulo: {module_name}')
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def profile_access_required(view_func):
    """
    Decorator that ensures user can only access their own profile
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Para vistas que requieren user_id en la URL
        user_id = kwargs.get('user_id') or kwargs.get('pk')
        
        if user_id and int(user_id) != request.user.id:
            # Solo roles con permisos especiales pueden ver otros perfiles
            if request.user.role and request.user.role.name not in ['Super Admin', 'Registro']:
                messages.error(request, 'Solo puedes acceder a tu propio perfil.')
                return redirect('accounts:profile')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def team_management_required(view_func):
    """
    Decorator for views that require team management permissions
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.role:
            messages.error(request, 'No tienes un rol asignado.')
            return redirect('core:dashboard')
        
        allowed_roles = ['Super Admin', 'Registro']
        if request.user.role.name not in allowed_roles:
            messages.error(request, 'No tienes permisos para gestionar equipos.')
            return redirect('core:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def sales_view_required(view_func):
    """
    Decorator for sales-related views that Ventas role can access
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.role:
            messages.error(request, 'No tienes un rol asignado.')
            return redirect('core:dashboard')
        
        allowed_roles = ['Super Admin', 'Registro', 'Ventas']
        if request.user.role.name not in allowed_roles:
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('core:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper