# apps/communications/views/lead_insights.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DateField
from django.db.models.functions import TruncDate, TruncHour, TruncWeek
from datetime import datetime, timedelta
from ..models import Lead, LeadAssignment, Conversacion, Mensaje
from ..services.lead_service import LeadService
from ..utils.permissions import require_lead_management_access
from apps.sales_team_management.models import OrganizationalUnit
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_lead_management_access
def lead_insights_dashboard(request):
    """
    Dashboard ejecutivo de insights de leads con métricas avanzadas y visualizaciones
    """
    now = timezone.now()
    today = now.date()
    
    # Períodos de tiempo
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_previous_month = (start_of_month - timedelta(days=1)).replace(day=1)
    end_of_previous_month = start_of_month - timedelta(days=1)
    
    # Obtener información del equipo del usuario para filtros de seguridad
    team_info = LeadService.get_user_team_info(request.user)
    
    # Query base de leads con filtros de seguridad
    leads_query = Lead.objects.filter(is_active=True)
    if team_info['is_team_member'] and team_info['user_team']:
        # Filtrar solo leads del equipo del usuario
        leads_query = leads_query.filter(
            assignments__organizational_unit=team_info['user_team'],
            assignments__is_active=True
        )
    
    # Query base de assignments (definir temprano para uso posterior)
    assignments_base_query = LeadAssignment.objects.filter(is_active=True)
    if team_info['is_team_member'] and team_info['user_team']:
        assignments_base_query = assignments_base_query.filter(
            organizational_unit=team_info['user_team']
        )
    
    # === MÉTRICAS PRINCIPALES ===
    yesterday = today - timedelta(days=1)
    leads_today = leads_query.filter(created_at__date=today).count()
    leads_yesterday = leads_query.filter(created_at__date=yesterday).count()
    
    # Esta semana vs semana anterior
    leads_this_week = leads_query.filter(created_at__date__gte=start_of_week).count()
    last_week_start = start_of_week - timedelta(days=7)
    last_week_end = start_of_week - timedelta(days=1)
    leads_last_week = leads_query.filter(
        created_at__date__gte=last_week_start,
        created_at__date__lte=last_week_end
    ).count()
    
    # Este mes vs mes anterior
    leads_this_month = leads_query.filter(created_at__date__gte=start_of_month).count()
    leads_previous_month = leads_query.filter(
        created_at__date__gte=start_of_previous_month,
        created_at__date__lte=end_of_previous_month
    ).count()
    
    # Leads asignados manualmente en los últimos 7 días
    seven_days_ago = today - timedelta(days=7)
    leads_assigned_last_7_days = assignments_base_query.filter(
        assigned_to_user__isnull=False,
        assigned_date__date__gte=seven_days_ago,
        assigned_date__date__lte=today
    ).count()
    
    # Total de assignments de los últimos 7 días (para calcular pendientes)
    total_assignments_last_7_days = assignments_base_query.filter(
        assigned_date__date__gte=seven_days_ago,
        assigned_date__date__lte=today
    ).count()
    
    # Leads pendientes en los últimos 7 días
    leads_pending_last_7_days = total_assignments_last_7_days - leads_assigned_last_7_days
    
    # Cálculo de crecimiento diario (hoy vs ayer)
    if leads_yesterday > 0:
        daily_growth = ((leads_today - leads_yesterday) / leads_yesterday) * 100
    else:
        daily_growth = leads_today * 100 if leads_today > 0 else 0
    
    # Cálculo de crecimiento mensual
    if leads_previous_month > 0:
        monthly_growth = ((leads_this_month - leads_previous_month) / leads_previous_month) * 100
    else:
        monthly_growth = leads_this_month * 100 if leads_this_month > 0 else 0
    
    # === MÉTRICAS DE CONVERSIÓN === 
    # Usar la misma lógica que /marketing/lead-management/ (LeadService.get_leads_stats)
    
    # Métricas reales de asignación manual (EXACTAMENTE como en LeadService)
    leads_asignados = assignments_base_query.filter(assigned_to_user__isnull=False).count()  # Asignados a vendedores
    leads_no_asignados = assignments_base_query.filter(assigned_to_user__isnull=True).count()  # Pendientes de asignación a vendedores
    
    # Tasa de asignación manual para las ÚLTIMAS 48 HORAS (2 días)
    two_days_ago = today - timedelta(days=2)
    assignments_last_48h = assignments_base_query.filter(
        assigned_date__date__gte=two_days_ago,
        assigned_date__date__lte=today
    )
    leads_assigned_48h = assignments_last_48h.filter(assigned_to_user__isnull=False).count()
    leads_pending_48h = assignments_last_48h.filter(assigned_to_user__isnull=True).count()
    total_assignments_48h = leads_assigned_48h + leads_pending_48h
    manual_assignment_rate_48h = (leads_assigned_48h / total_assignments_48h) * 100 if total_assignments_48h > 0 else 0
    
    # === ANÁLISIS POR FUERZA DE VENTAS ===
    sales_teams = OrganizationalUnit.objects.filter(unit_type='SALES', is_active=True)
    
    # Filtrar equipos según permisos
    if team_info['is_team_member'] and team_info['user_team']:
        sales_teams = sales_teams.filter(id=team_info['user_team'].id)
    
    team_performance = []
    for team in sales_teams:
        team_leads = leads_query.filter(
            assignments__organizational_unit=team,
            assignments__is_active=True
        ).distinct()
        
        team_leads_count = team_leads.count()
        team_leads_today = team_leads.filter(created_at__date=today).count()
        team_leads_week = team_leads.filter(created_at__date__gte=start_of_week).count()
        
        # Colores fijos por equipo
        team_colors = {
            'inversionistas': '#DC2626',      # Rojo
            'berchaticorp': '#1E3A8A',        # Azul oscuro
            'berchatti': '#1E3A8A',           # Azul oscuro (variación berchatti corp)
            'kibutz': '#0EA5E9',              # Celeste
            'royal': '#16A34A'                # Verde
        }
        
        # Buscar color por nombre del equipo (case insensitive)
        team_color = '#6B7280'  # Color por defecto (gris)
        for key, color in team_colors.items():
            if key.lower() in team.name.lower():
                team_color = color
                break
        
        team_performance.append({
            'team': team,
            'total_leads': team_leads_count,
            'leads_today': team_leads_today,
            'leads_week': team_leads_week,
            'color': team_color
        })
    
    # === DATOS PARA GRÁFICAS ===
    
    # Evolución de leads últimos 30 días
    thirty_days_ago = today - timedelta(days=30)
    daily_leads = leads_query.filter(
        created_at__date__gte=thirty_days_ago
    ).values('created_at__date').annotate(
        count=Count('id')
    ).order_by('created_at__date')
    
    # Completar días faltantes con 0
    evolution_data = {}
    current_date = thirty_days_ago
    while current_date <= today:
        evolution_data[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)
    
    for item in daily_leads:
        date_str = item['created_at__date'].strftime('%Y-%m-%d')
        evolution_data[date_str] = item['count']
    
    # Leads por hora del día (últimos 7 días)
    week_ago = today - timedelta(days=7)
    hourly_leads = leads_query.filter(
        created_at__date__gte=week_ago
    ).extra(
        select={'hour': "EXTRACT(hour FROM created_at)"}
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    hourly_data = {str(i): 0 for i in range(24)}
    for item in hourly_leads:
        hourly_data[str(int(item['hour']))] = item['count']
    
    # Distribución por canal/origen
    channel_distribution = leads_query.values('origen').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Estados de leads
    status_distribution = leads_query.values('estado').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # === MÉTRICAS AVANZADAS ===
    
    # Velocidad de asignación promedio
    recent_assignments = LeadAssignment.objects.filter(
        is_active=True,
        assigned_date__isnull=False,
        lead__created_at__date__gte=week_ago
    )
    
    assignment_times = []
    for assignment in recent_assignments:
        time_diff = (assignment.assigned_date - assignment.lead.created_at).total_seconds() / 60
        assignment_times.append(time_diff)
    
    avg_assignment_time = sum(assignment_times) / len(assignment_times) if assignment_times else 0
    
    # Formatear tiempo de asignación para el template
    if avg_assignment_time >= 60:
        avg_assignment_time_display = f"{avg_assignment_time/60:.1f}h"
    else:
        avg_assignment_time_display = f"{avg_assignment_time:.0f}min"
    
    
    # Cálculo de crecimientos y diferencias
    weekly_growth = ((leads_this_week - leads_last_week) / leads_last_week * 100) if leads_last_week > 0 else 100
    
    # Diferencias absolutas para el template
    week_diff = leads_this_week - leads_last_week
    month_diff = leads_this_month - leads_previous_month
    
    context = {
        'page_title': 'Información de Leads',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Información de Leads', 'url': None}
        ],
        
        # Métricas principales
        'leads_today': leads_today,
        'leads_yesterday': leads_yesterday,
        'leads_difference': abs(leads_today - leads_yesterday),
        'today_date': today,
        'yesterday_date': yesterday,
        'leads_this_week': leads_this_week,
        'leads_last_week': leads_last_week,
        'leads_this_month': leads_this_month,
        'leads_previous_month': leads_previous_month,
        'leads_assigned_last_7_days': leads_assigned_last_7_days,
        'leads_pending_last_7_days': leads_pending_last_7_days,
        'daily_growth': round(daily_growth, 1),
        'monthly_growth': round(monthly_growth, 1),
        'weekly_growth': round(weekly_growth, 1),
        
        # Diferencias calculadas
        'week_diff': week_diff,
        'month_diff': month_diff,
        'week_diff_abs': abs(week_diff),
        'month_diff_abs': abs(month_diff),
        
        # Métricas de conversión (data real de /marketing/lead-management/)
        'leads_asignados': leads_asignados,  # Asignados a vendedores específicos
        'leads_no_asignados': leads_no_asignados,  # Pendientes de asignación a vendedores
        'manual_assignment_rate_48h': round(manual_assignment_rate_48h, 1),  # Tasa últimas 48 horas
        'leads_assigned_48h': leads_assigned_48h,
        'leads_pending_48h': leads_pending_48h,
        'avg_assignment_time': round(avg_assignment_time, 1),
        'avg_assignment_time_display': avg_assignment_time_display,
        
        # Performance por equipos
        'team_performance': team_performance,
        'total_teams': len(team_performance),
        
        # Datos para gráficas (JSON)
        'evolution_data': json.dumps(evolution_data),
        'hourly_data': json.dumps(hourly_data),
        'channel_data': json.dumps(list(channel_distribution)),
        'status_data': json.dumps(list(status_distribution)),
        'team_names': json.dumps([t['team'].name for t in team_performance]),
        'team_leads': json.dumps([t['total_leads'] for t in team_performance]),
        'team_colors': json.dumps([t['color'] for t in team_performance]),
        
        # Configuración de usuario
        'can_view_all_teams': not team_info['is_team_member'],
        'user_team': team_info['user_team'],
    }
    
    return render(request, 'communications/insights/lead_insights_dashboard.html', context)