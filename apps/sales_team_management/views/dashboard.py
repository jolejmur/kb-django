# apps/sales_team_management/views/dashboard.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Case, When, IntegerField
from django.contrib.auth.models import User

from ..models import (
    EquipoVenta, GerenteEquipo, JefeVenta, 
    TeamLeader, Vendedor, ComisionVenta
)
from apps.real_estate_projects.models import Proyecto, Inmueble


@login_required
def sales_dashboard(request):
    """Dashboard principal de gestión de equipos de ventas"""
    
    # Estadísticas de equipos
    equipos_activos = EquipoVenta.objects.filter(activo=True)
    equipos_inactivos = EquipoVenta.objects.filter(activo=False)
    
    # Estadísticas de miembros del equipo
    gerentes_activos = GerenteEquipo.objects.filter(activo=True).count()
    gerentes_inactivos = GerenteEquipo.objects.filter(activo=False).count()
    
    jefes_activos = JefeVenta.objects.filter(activo=True).count()
    jefes_inactivos = JefeVenta.objects.filter(activo=False).count()
    
    leaders_activos = TeamLeader.objects.filter(activo=True).count()
    leaders_inactivos = TeamLeader.objects.filter(activo=False).count()
    
    vendedores_activos = Vendedor.objects.filter(activo=True).count()
    vendedores_inactivos = Vendedor.objects.filter(activo=False).count()
    
    total_miembros_activos = gerentes_activos + jefes_activos + leaders_activos + vendedores_activos
    total_miembros_inactivos = gerentes_inactivos + jefes_inactivos + leaders_inactivos + vendedores_inactivos
    
    # Estadísticas generales del sistema
    stats = {
        'total_equipos_activos': equipos_activos.count(),
        'total_equipos_inactivos': equipos_inactivos.count(),
        'total_proyectos': Proyecto.objects.filter(activo=True).count(),
        'total_inmuebles': Inmueble.objects.count(),
        'total_miembros_activos': total_miembros_activos,
        'total_miembros_inactivos': total_miembros_inactivos,
        'gerentes_activos': gerentes_activos,
        'jefes_activos': jefes_activos,
        'leaders_activos': leaders_activos,
        'vendedores_activos': vendedores_activos,
    }
    
    # Distribución por roles
    roles_distribution = {
        'gerentes': {'activos': gerentes_activos, 'inactivos': gerentes_inactivos},
        'jefes': {'activos': jefes_activos, 'inactivos': jefes_inactivos},
        'leaders': {'activos': leaders_activos, 'inactivos': leaders_inactivos},
        'vendedores': {'activos': vendedores_activos, 'inactivos': vendedores_inactivos},
    }

    # Equipos con más miembros (jerarquía completa)
    equipos_con_jerarquia = []
    for equipo in equipos_activos.order_by('nombre'):
        gerentes_count = equipo.gerenteequipo_set.filter(activo=True).count()
        jefes_count = 0
        leaders_count = 0
        vendedores_count = 0
        
        for gerente in equipo.gerenteequipo_set.filter(activo=True):
            jefes_activos_equipo = gerente.jefeventas.filter(activo=True)
            jefes_count += jefes_activos_equipo.count()
            
            for jefe in jefes_activos_equipo:
                leaders_activos_equipo = jefe.teamleaders.filter(activo=True)
                leaders_count += leaders_activos_equipo.count()
                
                for leader in leaders_activos_equipo:
                    vendedores_count += leader.vendedores.filter(activo=True).count()
        
        total_miembros = gerentes_count + jefes_count + leaders_count + vendedores_count
        
        equipos_con_jerarquia.append({
            'equipo': equipo,
            'gerentes': gerentes_count,
            'jefes': jefes_count,
            'leaders': leaders_count,
            'vendedores': vendedores_count,
            'total_miembros': total_miembros,
            'tiene_configuracion_completa': gerentes_count > 0 and hasattr(equipo, 'comision_venta') and equipo.comision_venta is not None,
        })
    
    # Ordenar por total de miembros
    equipos_con_jerarquia.sort(key=lambda x: x['total_miembros'], reverse=True)
    
    # Equipos sin configurar
    equipos_sin_gerente = EquipoVenta.objects.filter(
        activo=True,
        gerenteequipo__isnull=True
    ).distinct()
    
    equipos_sin_comisiones = EquipoVenta.objects.filter(
        activo=True,
        comision_venta__isnull=True
    )

    # Proyectos más activos
    proyectos_activos = Proyecto.objects.filter(
        activo=True
    ).annotate(
        total_inmuebles=Count('fases__inmuebles'),
        inmuebles_vendidos=Count('fases__inmuebles', filter=Q(fases__inmuebles__estado='vendido'))
    ).order_by('-total_inmuebles')[:5]

    # Alertas y recomendaciones
    alertas = []
    if equipos_sin_gerente.exists():
        alertas.append({
            'tipo': 'warning',
            'titulo': 'Equipos sin Gerente',
            'mensaje': f'{equipos_sin_gerente.count()} equipos no tienen gerente asignado',
            'url': 'sales:equipos_list'
        })
    
    if equipos_sin_comisiones.exists():
        alertas.append({
            'tipo': 'info',
            'titulo': 'Equipos sin Comisiones',
            'mensaje': f'{equipos_sin_comisiones.count()} equipos no tienen comisiones configuradas',
            'url': 'sales:equipos_list'
        })

    context = {
        'stats': stats,
        'roles_distribution': roles_distribution,
        'equipos_con_jerarquia': equipos_con_jerarquia[:8],  # Top 8 equipos
        'proyectos_activos': proyectos_activos,
        'equipos_sin_gerente': equipos_sin_gerente,
        'equipos_sin_comisiones': equipos_sin_comisiones,
        'alertas': alertas,
        'title': 'Dashboard - Gestión de Equipos de Ventas',
    }
    return render(request, 'sales_team_management/dashboard.html', context)