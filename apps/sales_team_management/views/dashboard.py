# apps/sales_team_management/views/dashboard.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Case, When, IntegerField, Avg
from django.contrib.auth.models import User

# NUEVO MODELO - Sin Legacy
from ..models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)
from apps.real_estate_projects.models import Proyecto, Inmueble


@login_required
def sales_dashboard(request):
    """Dashboard principal de gestión de equipos usando el nuevo modelo"""
    
    # Estadísticas de unidades organizacionales
    units_activas = OrganizationalUnit.objects.filter(is_active=True)
    units_inactivas = OrganizationalUnit.objects.filter(is_active=False)
    
    # Estadísticas de membresías por posición
    memberships_activas = TeamMembership.objects.filter(is_active=True)
    memberships_inactivas = TeamMembership.objects.filter(is_active=False)
    
    # Contar por tipo de posición
    position_stats = {}
    for position in PositionType.objects.filter(is_active=True):
        activos = memberships_activas.filter(position_type=position).count()
        inactivos = memberships_inactivas.filter(position_type=position).count()
        position_stats[position.code] = {
            'name': position.name,
            'activos': activos,
            'inactivos': inactivos
        }
    
    total_miembros_activos = memberships_activas.count()
    total_miembros_inactivos = memberships_inactivas.count()
    
    # Estadísticas generales del sistema
    stats = {
        'total_equipos_activos': units_activas.count(),
        'total_equipos_inactivos': units_inactivas.count(),
        'total_proyectos': Proyecto.objects.filter(activo=True).count(),
        'total_inmuebles': Inmueble.objects.count(),
        'total_miembros_activos': total_miembros_activos,
        'total_miembros_inactivos': total_miembros_inactivos,
        'total_relaciones_jerarquicas': HierarchyRelation.objects.filter(is_active=True).count(),
        'total_estructuras_comision': CommissionStructure.objects.filter(is_active=True).count(),
    }
    
    # Distribución por tipos de unidad
    unit_type_distribution = units_activas.values('unit_type').annotate(
        count=Count('id')
    ).order_by('unit_type')
    
    # Equipos con información detallada
    equipos_con_info = []
    for unit in units_activas.annotate(
        total_members=Count('teammembership', filter=Q(teammembership__is_active=True))
    ).order_by('name'):
        
        # Contar por posición
        members_by_position = {}
        for membership in unit.teammembership_set.filter(is_active=True).select_related('position_type'):
            pos_code = membership.position_type.code
            if pos_code not in members_by_position:
                members_by_position[pos_code] = 0
            members_by_position[pos_code] += 1
        
        # Verificar si tiene estructura de comisiones
        has_commission_structure = CommissionStructure.objects.filter(
            organizational_unit=unit,
            is_active=True
        ).exists()
        
        # Obtener relaciones jerárquicas
        hierarchy_relations_count = HierarchyRelation.objects.filter(
            supervisor_membership__organizational_unit=unit,
            is_active=True
        ).count()
        
        equipos_con_info.append({
            'unit': unit,
            'total_members': unit.total_members,
            'members_by_position': members_by_position,
            'has_commission_structure': has_commission_structure,
            'hierarchy_relations_count': hierarchy_relations_count,
            'completion_score': calculate_team_completion_score(unit, members_by_position, has_commission_structure, hierarchy_relations_count)
        })
    
    # Ordenar por puntuación de completitud
    equipos_con_info.sort(key=lambda x: x['completion_score'], reverse=True)
    
    # Unidades sin configurar completamente
    units_sin_miembros = units_activas.annotate(
        members_count=Count('teammembership', filter=Q(teammembership__is_active=True))
    ).filter(members_count=0)
    
    units_sin_comisiones = units_activas.filter(
        commissionstructure__isnull=True
    ) | units_activas.filter(
        commissionstructure__is_active=False
    )
    
    # Análisis de jerarquías
    hierarchy_analysis = analyze_hierarchy_health()
    
    # Proyectos más activos (mantener lógica original)
    proyectos_activos = Proyecto.objects.filter(
        activo=True
    ).annotate(
        total_inmuebles=Count('fases__inmuebles'),
        inmuebles_vendidos=Count('fases__inmuebles', filter=Q(fases__inmuebles__estado='vendido'))
    ).order_by('-total_inmuebles')[:5]

    # Alertas y recomendaciones
    alertas = []
    if units_sin_miembros.exists():
        alertas.append({
            'tipo': 'warning',
            'titulo': 'Unidades sin Miembros',
            'mensaje': f'{units_sin_miembros.count()} unidades no tienen miembros asignados',
            'url': 'sales_team_management:equipos_list'
        })
    
    if units_sin_comisiones.exists():
        alertas.append({
            'tipo': 'info',
            'titulo': 'Unidades sin Comisiones',
            'mensaje': f'{units_sin_comisiones.count()} unidades no tienen estructura de comisiones',
            'url': 'sales_team_management:equipos_list'
        })
    
    if hierarchy_analysis['inconsistencies_count'] > 0:
        alertas.append({
            'tipo': 'danger',
            'titulo': 'Inconsistencias en Jerarquía',
            'mensaje': f'{hierarchy_analysis["inconsistencies_count"]} inconsistencias detectadas en las relaciones jerárquicas',
            'url': 'sales_team_management:analisis_jerarquia'
        })

    context = {
        'stats': stats,
        'position_stats': position_stats,
        'unit_type_distribution': unit_type_distribution,
        'equipos_con_info': equipos_con_info[:8],  # Top 8 equipos
        'proyectos_activos': proyectos_activos,
        'units_sin_miembros': units_sin_miembros,
        'units_sin_comisiones': units_sin_comisiones,
        'hierarchy_analysis': hierarchy_analysis,
        'alertas': alertas,
        'title': 'Dashboard - Gestión de Equipos de Ventas',
    }
    return render(request, 'sales_team_management/dashboard.html', context)


# ============================================================
# FUNCIONES AUXILIARES PARA EL DASHBOARD
# ============================================================

def calculate_team_completion_score(unit, members_by_position, has_commission_structure, hierarchy_relations_count):
    """Calcula un puntaje de completitud para el equipo"""
    score = 0
    
    # Puntos por tener miembros
    total_members = sum(members_by_position.values())
    if total_members > 0:
        score += 30
    
    # Puntos por diversidad de posiciones
    position_diversity = len(members_by_position)
    score += min(position_diversity * 10, 30)  # Max 30 puntos
    
    # Puntos por estructura de comisiones
    if has_commission_structure:
        score += 20
    
    # Puntos por relaciones jerárquicas
    if hierarchy_relations_count > 0:
        score += 20
    
    return score


def analyze_hierarchy_health():
    """Analiza la salud general de las estructuras jerárquicas"""
    
    total_relations = HierarchyRelation.objects.filter(is_active=True).count()
    
    # Detectar inconsistencias básicas
    inconsistencies_count = 0
    
    # Relaciones circulares
    circular_relations = detect_circular_relations()
    inconsistencies_count += len(circular_relations)
    
    # Múltiples supervisores primarios
    multiple_primary_supervisors = HierarchyRelation.objects.filter(
        is_active=True,
        is_primary=True
    ).values('subordinate_membership').annotate(
        count=Count('id')
    ).filter(count__gt=1).count()
    
    inconsistencies_count += multiple_primary_supervisors
    
    # Estadísticas por tipo de relación
    relation_type_stats = HierarchyRelation.objects.filter(
        is_active=True
    ).values('relation_type').annotate(
        count=Count('id')
    )
    
    return {
        'total_relations': total_relations,
        'inconsistencies_count': inconsistencies_count,
        'circular_relations_count': len(circular_relations),
        'multiple_primary_supervisors_count': multiple_primary_supervisors,
        'relation_type_stats': list(relation_type_stats)
    }


def detect_circular_relations():
    """Detecta relaciones circulares en la jerarquía"""
    circular_relations = []
    
    relations = HierarchyRelation.objects.filter(is_active=True)
    
    for relation in relations:
        # Buscar si existe una relación que cree un ciclo
        reverse_relation = HierarchyRelation.objects.filter(
            supervisor_membership=relation.subordinate_membership,
            subordinate_membership=relation.supervisor_membership,
            is_active=True
        ).first()
        
        if reverse_relation:
            circular_relations.append({
                'relation_1': relation,
                'relation_2': reverse_relation
            })
    
    return circular_relations