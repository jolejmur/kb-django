from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q
from apps.accounts.decorators import role_required

User = get_user_model()


@login_required
def lead_assignment_report(request):
    """
    Reporte de usuarios que pueden asignar leads a vendedores.
    
    Este reporte muestra todos los usuarios que tienen los permisos necesarios
    para asignar leads basado en sus roles y permisos del sistema.
    """
    
    # Buscar usuarios que pueden asignar leads basado en permisos
    # Los usuarios que pueden asignar leads son aquellos con:
    # 1. Permisos de gestión de leads
    # 2. Permisos de distribución de leads 
    # 3. Roles de supervisión (gerentes, jefes de venta, team leaders)
    
    # Obtener grupos/permisos relacionados con asignación de leads
    lead_assignment_groups = Group.objects.filter(
        Q(name__icontains='lead') |
        Q(name__icontains='distribución') |
        Q(name__icontains='gestión de equipos') |
        Q(name__icontains='chat') |
        Q(name__icontains='comunicaciones') |
        Q(name__icontains='ventas')
    )
    
    # Usuarios que pueden asignar leads
    users_who_can_assign = User.objects.filter(
        Q(is_superuser=True) |  # Superusuarios siempre pueden
        Q(role__groups__in=lead_assignment_groups) |  # Usuarios con roles que incluyen estos grupos
        Q(groups__in=lead_assignment_groups)  # Usuarios directamente asignados a estos grupos
    ).distinct().select_related('role').prefetch_related('role__groups', 'groups')
    
    # Filtrar solo usuarios activos
    users_who_can_assign = users_who_can_assign.filter(is_active=True)
    
    # Categorizar usuarios por tipo de rol
    user_categories = {
        'superusuarios': [],
        'gerentes': [],
        'jefes_venta': [],
        'team_leaders': [],
        'supervisores_chat': [],
        'administradores': [],
        'otros': []
    }
    
    for user in users_who_can_assign:
        user_info = {
            'user': user,
            'role_name': user.role.name if user.role else 'Sin rol',
            'groups': user.role.groups.all() if user.role else user.groups.all(),
            'permissions_summary': get_user_permissions_summary(user),
            'can_assign_reason': get_assignment_reason(user, lead_assignment_groups)
        }
        
        if user.is_superuser:
            user_categories['superusuarios'].append(user_info)
        elif user.role and 'gerente' in user.role.name.lower():
            user_categories['gerentes'].append(user_info)
        elif user.role and ('jefe' in user.role.name.lower() or 'venta' in user.role.name.lower()):
            user_categories['jefes_venta'].append(user_info)
        elif user.role and ('leader' in user.role.name.lower() or 'líder' in user.role.name.lower()):
            user_categories['team_leaders'].append(user_info)
        elif user.role and ('chat' in user.role.name.lower() or 'comunicaci' in user.role.name.lower() or 'supervisor' in user.role.name.lower()):
            user_categories['supervisores_chat'].append(user_info)
        elif user.role and 'admin' in user.role.name.lower():
            user_categories['administradores'].append(user_info)
        else:
            user_categories['otros'].append(user_info)
    
    # Estadísticas del reporte
    stats = {
        'total_users': users_who_can_assign.count(),
        'by_category': {k: len(v) for k, v in user_categories.items()},
        'active_roles': len(set(user.role.name for user in users_who_can_assign if user.role)),
        'relevant_groups': lead_assignment_groups.count()
    }
    
    context = {
        'user_categories': user_categories,
        'stats': stats,
        'lead_assignment_groups': lead_assignment_groups,
        'title': 'Reporte: Usuarios que pueden asignar leads'
    }
    
    return render(request, 'groups/reports/lead_assignment_report.html', context)


def get_user_permissions_summary(user):
    """
    Obtiene un resumen de los permisos del usuario relacionados con leads
    """
    permissions = []
    
    if user.is_superuser:
        permissions.append('Superusuario - Todos los permisos')
        return permissions
    
    # Obtener permisos del rol
    if user.role:
        for group in user.role.groups.all():
            group_permissions = group.permissions.filter(
                Q(codename__icontains='lead') |
                Q(codename__icontains='assign') |
                Q(codename__icontains='distribution') |
                Q(content_type__model__icontains='lead')
            )
            for perm in group_permissions:
                permissions.append(f"{group.name}: {perm.name}")
    
    # Obtener permisos directos del usuario
    user_permissions = user.user_permissions.filter(
        Q(codename__icontains='lead') |
        Q(codename__icontains='assign') |
        Q(codename__icontains='distribution') |
        Q(content_type__model__icontains='lead')
    )
    for perm in user_permissions:
        permissions.append(f"Directo: {perm.name}")
    
    return permissions if permissions else ['Sin permisos específicos de leads']


def get_assignment_reason(user, lead_assignment_groups):
    """
    Explica por qué un usuario puede asignar leads
    """
    reasons = []
    
    if user.is_superuser:
        reasons.append("Es superusuario")
    
    if user.role:
        matching_groups = user.role.groups.filter(id__in=lead_assignment_groups)
        if matching_groups.exists():
            reasons.append(f"Su rol '{user.role.name}' incluye: {', '.join(matching_groups.values_list('name', flat=True))}")
    
    user_groups = user.groups.filter(id__in=lead_assignment_groups)
    if user_groups.exists():
        reasons.append(f"Asignado directamente a: {', '.join(user_groups.values_list('name', flat=True))}")
    
    return reasons if reasons else ["Acceso indirecto a través de permisos"]


@login_required
def reports_dashboard(request):
    """
    Dashboard principal del módulo de reportes
    """
    context = {
        'title': 'Dashboard de Reportes',
        'available_reports': [
            {
                'name': 'Usuarios que pueden asignar leads',
                'description': 'Muestra todos los usuarios que tienen permisos para asignar leads a vendedores',
                'url': 'groups:lead_assignment_report',
                'icon': 'fas fa-user-tie',
                'category': 'Gestión de Leads'
            },
            # Aquí se pueden agregar más reportes en el futuro
        ]
    }
    
    return render(request, 'groups/reports/dashboard.html', context)
