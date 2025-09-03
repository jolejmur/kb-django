# apps/communications/views/lead_management.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from urllib.parse import urlencode
from ..models import Lead, LeadAssignment
from ..services.lead_service import LeadService
from ..utils.permissions import require_lead_management_access
from ..utils.filters import LeadFilters, PaginationHelper
from ..utils.formatters import DataFormatter
from apps.sales_team_management.models import OrganizationalUnit
import logging

logger = logging.getLogger(__name__)


@login_required
@require_lead_management_access
def lead_management_dashboard(request):
    """
    Panel principal de Gestión de Leads - Nueva vista mejorada
    """
    # Obtener información del equipo del usuario y validar seguridad
    team_info = LeadService.get_user_team_info(request.user)
    
    # Validar filtros de seguridad
    requested_filter = request.GET.get('sales_unit', '')
    is_valid, validated_filter = LeadService.validate_team_filter_security(request.user, requested_filter)
    
    if not is_valid:
        # Intento de manipulación - redirigir con filtro correcto
        query_params = request.GET.copy()
        query_params['sales_unit'] = validated_filter
        return HttpResponseRedirect(f"{request.path}?{urlencode(query_params)}")
    
    sales_unit_filter = validated_filter
    
    # Obtener estadísticas
    stats = LeadService.get_leads_stats(request.user, sales_unit_filter)
    
    # Estadísticas por fuerza de venta (filtradas por acceso de equipo)
    sales_units_stats = []
    
    # Filtrar equipos según el control de acceso
    if team_info['can_change_filter']:
        # Usuario sin equipo - ver todos los equipos
        units_query = OrganizationalUnit.objects.filter(unit_type='SALES', is_active=True)
    else:
        # Usuario de equipo - solo su equipo
        units_query = OrganizationalUnit.objects.filter(
            id=team_info['user_team'].id, 
            unit_type='SALES', 
            is_active=True
        )
    
    for unit in units_query:
        try:
            config = unit.lead_distribution
            unit_stats = {
                'unit': unit,
                'config': config,
                'leads_today': config.current_leads_today,
                'leads_week': config.current_leads_this_week,
                'percentage': float(config.distribution_percentage),
                'is_active': config.is_active_for_leads,
                'can_receive_more': config.can_receive_more_leads,
                'team_members': unit.teammembership_set.filter(
                    is_active=True, status='ACTIVE'
                ).count()
            }
        except:
            unit_stats = {
                'unit': unit,
                'config': None,
                'leads_today': 0,
                'leads_week': 0,
                'percentage': 0,
                'is_active': False,
                'can_receive_more': False,
                'team_members': unit.teammembership_set.filter(
                    is_active=True, status='ACTIVE'
                ).count()
            }
        sales_units_stats.append(unit_stats)
    
    # Obtener filtros de la URL
    filters = {
        'assignment_status': request.GET.get('assignment_status', 'assigned_to_unit'),
        'lead_status': request.GET.get('lead_status', ''),
        'sales_unit': sales_unit_filter
    }
    
    # Obtener leads filtrados
    leads_query = LeadService.get_filtered_leads(request.user, filters)
    logger.info(f"🔍 DEBUG lead_management_dashboard: user={request.user.username}, filters={filters}")
    logger.info(f"🔍 DEBUG leads_query inicial: {leads_query.count()} leads")
    
    # Aplicar filtros adicionales de la vista
    if filters['assignment_status'] == 'unassigned':
        leads_query = leads_query.exclude(assignments__is_active=True)
        logger.info(f"🔍 DEBUG filtro 'unassigned': {leads_query.count()} leads")
    elif filters['assignment_status'] == 'assigned_to_unit':
        leads_query = leads_query.filter(
            assignments__is_active=True,
            assignments__assigned_to_user__isnull=True
        )
        logger.info(f"🔍 DEBUG filtro 'assigned_to_unit': {leads_query.count()} leads")
    elif filters['assignment_status'] == 'assigned_to_user':
        leads_query = leads_query.filter(
            assignments__is_active=True,
            assignments__assigned_to_user__isnull=False
        )
        logger.info(f"🔍 DEBUG filtro 'assigned_to_user': {leads_query.count()} leads")
    elif filters['assignment_status'] == 'all_assigned':
        leads_query = leads_query.filter(assignments__is_active=True)
        logger.info(f"🔍 DEBUG filtro 'all_assigned': {leads_query.count()} leads")
    
    # Aplicar filtros adicionales si se especifican
    # NOTA: El filtro de sales_unit ya se aplica en get_accessible_leads_for_management para usuarios con equipo
    # Solo aplicamos este filtro para usuarios sin equipo específico (admin, etc.) que pueden cambiar filtros
    if sales_unit_filter and team_info['can_change_filter']:
        leads_query = leads_query.filter(
            assignments__organizational_unit_id=sales_unit_filter,
            assignments__is_active=True
        )
        logger.info(f"🔍 DEBUG filtro sales_unit {sales_unit_filter}: {leads_query.count()} leads")
    
    logger.info(f"🔍 DEBUG query final: {leads_query.count()} leads")
    
    # Leads recientes
    recent_leads = leads_query.select_related('cliente').prefetch_related(
        'assignments__organizational_unit',
        'assignments__assigned_to_user'
    ).order_by('-fecha_primera_interaccion')[:10]
    
    # Asignaciones recientes
    recent_assignments_query = LeadAssignment.objects.filter(is_active=True)
    if team_info['is_team_member'] and team_info['user_team']:
        recent_assignments_query = recent_assignments_query.filter(
            organizational_unit=team_info['user_team']
        )
    
    recent_assignments = recent_assignments_query.select_related(
        'lead__cliente', 'organizational_unit', 'assigned_to_user'
    ).order_by('-assigned_date')[:15]
    
    # Paginación
    page = request.GET.get('page', 1)
    paginator = Paginator(leads_query.order_by('-fecha_primera_interaccion'), 10)
    
    try:
        filtered_leads = paginator.page(page)
    except:
        filtered_leads = paginator.page(1)

    context = {
        'stats': {
            'total_leads': stats['total_leads'],
            'leads_without_assignment': stats['no_asignados'],
            'leads_assigned_today': stats['leads_hoy'],
            'leads_this_week': stats['leads_semana'],
            'active_sales_units': len([u for u in sales_units_stats if u['is_active']]),
            'total_sales_units': len(sales_units_stats),
        },
        'sales_units_stats': sales_units_stats,
        'recent_leads': recent_leads,
        'filtered_leads': filtered_leads,
        'recent_assignments': recent_assignments,
        'sales_units': units_query.order_by('name'),
        'current_filters': filters,
        'lead_states': Lead.ESTADOS_LEAD,
        'page_title': 'Asignación de Leads',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Asignación de Leads', 'url': None}
        ],
        # Control de acceso por equipo
        'user_team': team_info['user_team'],
        'is_team_member': team_info['is_team_member'],
        'can_change_filter': team_info['can_change_filter'],
    }
    
    return render(request, 'communications/lead_management_dashboard.html', context)




@login_required
@require_lead_management_access
def lead_distribution_config(request):
    """
    Vista para configurar la distribución de leads por equipos
    """
    # Obtener configuraciones de todos los equipos
    configs = LeadService.get_all_distribution_configs()
    
    # Obtener estadísticas generales
    stats = LeadService.get_distribution_stats()
    
    # Obtener asignaciones recientes
    recent_assignments = LeadAssignment.objects.filter(
        is_active=True,
        assigned_date__isnull=False
    ).select_related(
        'lead', 'organizational_unit', 'assigned_to_user'
    ).order_by('-assigned_date')[:10]
    
    # Calcular porcentajes totales
    total_percentage = sum(config.distribution_percentage for config in configs)
    percentage_remaining = max(0, 100 - total_percentage)
    
    context = {
        'configs': configs,
        'stats': stats,
        'recent_assignments': recent_assignments,
        'total_percentage': total_percentage,
        'percentage_remaining': percentage_remaining,
        'page_title': 'Configuración de Distribución',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Configuración de Distribución', 'url': None}
        ],
    }
    
    return render(request, 'communications/lead_distribution/config.html', context)


@login_required
@require_lead_management_access
def lead_assignments_history(request):
    """
    Vista del historial de asignaciones de leads
    """
    team_info = LeadService.get_user_team_info(request.user)
    
    # Query base de asignaciones
    assignments_query = LeadAssignment.objects.filter(is_active=True)
    
    # Aplicar filtros de equipo si corresponde
    if team_info['is_team_member'] and team_info['user_team']:
        assignments_query = assignments_query.filter(
            organizational_unit=team_info['user_team']
        )
    
    # Filtros adicionales
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    unit_filter = request.GET.get('unit')
    
    if date_from:
        assignments_query = assignments_query.filter(assigned_date__date__gte=date_from)
    if date_to:
        assignments_query = assignments_query.filter(assigned_date__date__lte=date_to)
    if unit_filter and team_info['can_change_filter']:
        assignments_query = assignments_query.filter(organizational_unit_id=unit_filter)
    
    # Paginación
    page = request.GET.get('page', 1)
    pagination_data = PaginationHelper.paginate_queryset(
        assignments_query.select_related(
            'lead__cliente', 'organizational_unit', 'assigned_to_user', 'assigned_by'
        ).order_by('-assigned_date'),
        page, 20
    )
    
    # Equipos disponibles para filtro
    units_query = OrganizationalUnit.objects.filter(unit_type='SALES', is_active=True)
    if not team_info['can_change_filter']:
        units_query = units_query.filter(id=team_info['user_team'].id)
    
    context = {
        'assignments': pagination_data['items'],
        'pagination': pagination_data,
        'units': units_query.order_by('name'),
        'current_filters': {
            'date_from': date_from,
            'date_to': date_to,
            'unit': unit_filter
        },
        'page_title': 'Historial de Asignaciones',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Historial de Asignaciones', 'url': None}
        ],
        'can_change_filter': team_info['can_change_filter'],
    }
    
    return render(request, 'communications/lead_distribution/history.html', context)