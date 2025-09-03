"""
Views for handling permission errors and access denied scenarios
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


@login_required
def permission_denied_view(request, permission_required=None, section_name=None):
    """
    Vista genérica para mostrar error de permisos denegados
    """
    # Determinar la sección basada en el permiso requerido
    section_info = get_section_info(permission_required)
    
    # Si viene información específica, usarla
    if section_name:
        section_info['name'] = section_name
    
    context = {
        'error_title': 'Acceso Denegado',
        'error_message': f'No tienes permisos para acceder a {section_info["name"]}.',
        'section_info': section_info,
        'user_permissions': get_user_permission_summary(request.user),
        'suggested_actions': get_suggested_actions(request.user, section_info),
    }
    
    # Si es una petición AJAX, devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'error': True,
            'message': context['error_message'],
            'permission_required': permission_required,
            'section': section_info['name']
        }, status=403)
    
    return render(request, 'sales_team_management/errors/permission_denied.html', context, status=403)


def get_section_info(permission_required):
    """
    Obtiene información de la sección basada en el permiso requerido
    """
    section_map = {
        # Equipos
        'sales_team_management.view_organizationalunit': {
            'name': 'Gestión de Equipos',
            'icon': 'fas fa-users',
            'color': 'blue',
            'description': 'Visualización de unidades organizacionales y equipos de trabajo'
        },
        'sales_team_management.add_organizationalunit': {
            'name': 'Creación de Equipos',
            'icon': 'fas fa-plus-circle',
            'color': 'green',
            'description': 'Creación de nuevas unidades organizacionales'
        },
        
        # Jerarquía
        'sales_team_management.view_hierarchyrelation': {
            'name': 'Jerarquía Organizacional',
            'icon': 'fas fa-sitemap',
            'color': 'purple',
            'description': 'Visualización de relaciones jerárquicas entre equipos'
        },
        'sales_team_management.add_hierarchyrelation': {
            'name': 'Gestión de Jerarquías',
            'icon': 'fas fa-project-diagram',
            'color': 'purple',
            'description': 'Creación y modificación de relaciones jerárquicas'
        },
        
        # Comisiones
        'sales_team_management.view_commissionstructure': {
            'name': 'Estructura de Comisiones',
            'icon': 'fas fa-calculator',
            'color': 'orange',
            'description': 'Visualización y gestión de estructuras de comisiones'
        },
    }
    
    return section_map.get(permission_required, {
        'name': 'Esta Sección',
        'icon': 'fas fa-lock',
        'color': 'gray',
        'description': 'Funcionalidad del sistema'
    })


def get_user_permission_summary(user):
    """
    Obtiene un resumen de los permisos del usuario
    """
    if not user.role:
        return {
            'role': 'Sin rol asignado',
            'groups': [],
            'accessible_sections': []
        }
    
    # Mapear permisos a secciones accesibles
    accessible_sections = []
    
    if user.has_perm('sales_team_management.view_organizationalunit'):
        accessible_sections.append({
            'name': 'Gestión de Equipos',
            'url': '/sales/equipos/',
            'icon': 'fas fa-users',
            'color': 'blue'
        })
    
    if user.has_perm('sales_team_management.view_hierarchyrelation'):
        accessible_sections.append({
            'name': 'Jerarquía Organizacional', 
            'url': '/sales/jerarquia/',
            'icon': 'fas fa-sitemap',
            'color': 'purple'
        })
    
    if user.has_perm('sales_team_management.view_commissionstructure'):
        accessible_sections.append({
            'name': 'Estructura de Comisiones',
            'url': '/sales/comisiones/equipos/',
            'icon': 'fas fa-calculator',
            'color': 'orange' 
        })
    
    return {
        'role': user.role.name,
        'groups': [group.name for group in user.role.groups.all()],
        'accessible_sections': accessible_sections
    }


def get_suggested_actions(user, section_info):
    """
    Obtiene acciones sugeridas para el usuario
    """
    actions = []
    
    # Siempre sugerir contactar administrador
    actions.append({
        'title': 'Contactar Administrador',
        'description': f'Solicita acceso al módulo "{section_info["name"]}" al administrador del sistema',
        'icon': 'fas fa-user-shield',
        'type': 'contact'
    })
    
    # Si tiene algunos permisos, sugerir secciones accesibles
    accessible_sections = get_user_permission_summary(user)['accessible_sections']
    if accessible_sections:
        actions.append({
            'title': 'Ir a Secciones Disponibles',
            'description': 'Accede a las funcionalidades que tienes disponibles',
            'icon': 'fas fa-arrow-right',
            'type': 'redirect',
            'sections': accessible_sections
        })
    
    # Sugerir volver al dashboard
    actions.append({
        'title': 'Volver al Dashboard',
        'description': 'Regresa al panel principal del sistema',
        'icon': 'fas fa-home',
        'type': 'dashboard',
        'url': '/dashboard/'
    })
    
    return actions