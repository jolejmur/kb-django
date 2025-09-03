"""
Module-specific decorators for route access control
These use NEW permissions without affecting existing ones
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from .views.permission_views import permission_denied_view


def team_management_module_required(view_func):
    """
    Decorator that requires view_organizationalunit permission
    for /sales/team-management/ routes
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_perm('sales_team_management.view_organizationalunit'):
            return permission_denied_view(
                request, 
                permission_required='sales_team_management.view_organizationalunit',
                section_name='Gestión de Equipos'
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def hierarchy_module_required(view_func):
    """
    Decorator that requires view_hierarchyrelation permission
    for /sales/hierarchy/ routes
    """
    @wraps(view_func)
    @login_required  
    def wrapper(request, *args, **kwargs):
        if not request.user.has_perm('sales_team_management.view_hierarchyrelation'):
            return permission_denied_view(
                request,
                permission_required='sales_team_management.view_hierarchyrelation', 
                section_name='Jerarquía de Equipos'
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def commissions_module_required(view_func):
    """
    Decorator that requires view_commissionstructure permission
    for /sales/commissions/ routes
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_perm('sales_team_management.view_commissionstructure'):
            return permission_denied_view(
                request,
                permission_required='sales_team_management.view_commissionstructure',
                section_name='Comisiones'
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def dashboard_module_required(view_func):
    """
    Decorator that requires access_dashboard_module permission
    for /sales/dashboard/ routes
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_perm('sales_team_management.access_dashboard_module'):
            return permission_denied_view(
                request,
                permission_required='sales_team_management.access_dashboard_module',
                section_name='Dashboard de Equipos'
            )
        return view_func(request, *args, **kwargs)
    return wrapper