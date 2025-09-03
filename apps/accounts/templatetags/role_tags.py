"""
Template tags for role-based permission checking
"""
from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.simple_tag(takes_context=True)
def has_role(context, role_name):
    """
    Check if current user has a specific role
    Usage: {% has_role 'Ventas' as is_ventas %}
    """
    request = context['request']
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    
    if not request.user.role:
        return False
    
    return request.user.role.name == role_name


@register.simple_tag(takes_context=True)
def has_any_role(context, *role_names):
    """
    Check if current user has any of the specified roles
    Usage: {% has_any_role 'Ventas' 'Registro' as can_access %}
    """
    request = context['request']
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    
    if not request.user.role:
        return False
    
    return request.user.role.name in role_names


@register.simple_tag(takes_context=True)
def has_module_access(context, module_name):
    """
    Check if current user has access to a specific module
    Usage: {% has_module_access 'Gestión de Equipos' as can_manage_teams %}
    """
    request = context['request']
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    
    return request.user.has_module_access(module_name)


@register.simple_tag(takes_context=True)
def can_manage_teams(context):
    """
    Check if current user can manage teams
    Usage: {% can_manage_teams as can_manage %}
    """
    request = context['request']
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    
    if not request.user.role:
        return False
    
    allowed_roles = ['Super Admin', 'Registro']
    return request.user.role.name in allowed_roles


@register.simple_tag(takes_context=True)
def can_view_hierarchy(context):
    """
    Check if current user can view team hierarchy
    Usage: {% can_view_hierarchy as can_view %}
    """
    request = context['request']
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    
    if not request.user.role:
        return False
    
    allowed_roles = ['Super Admin', 'Registro']
    return request.user.role.name in allowed_roles


@register.simple_tag(takes_context=True)
def is_profile_owner(context, profile_user_id):
    """
    Check if current user is the owner of the profile being viewed
    Usage: {% is_profile_owner user.id as is_owner %}
    """
    request = context['request']
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    
    return request.user.id == profile_user_id


@register.simple_tag(takes_context=True)
def can_edit_profile(context, profile_user_id):
    """
    Check if current user can edit a specific profile
    Usage: {% can_edit_profile user.id as can_edit %}
    """
    request = context['request']
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    
    # Users can always edit their own profile
    if request.user.id == profile_user_id:
        return True
    
    # Only certain roles can edit other profiles
    if not request.user.role:
        return False
    
    privileged_roles = ['Super Admin', 'Registro']
    return request.user.role.name in privileged_roles


@register.filter
def user_role_name(user):
    """
    Get the role name of a user
    Usage: {{ user|user_role_name }}
    """
    if hasattr(user, 'role') and user.role:
        return user.role.name
    return 'Sin rol'


@register.inclusion_tag('accounts/partials/role_badge.html')
def role_badge(user):
    """
    Display a role badge for a user
    Usage: {% role_badge user %}
    """
    role_colors = {
        'Super Admin': 'danger',
        'Registro': 'primary',
        'Gerente de Proyecto': 'warning',
        'Gerente de Equipo': 'info', 
        'Team Leader': 'secondary',
        'Ventas': 'success',
    }
    
    role_name = 'Sin rol'
    role_color = 'secondary'
    
    if hasattr(user, 'role') and user.role:
        role_name = user.role.name
        role_color = role_colors.get(role_name, 'info')
    
    return {
        'role_name': role_name,
        'role_color': role_color
    }