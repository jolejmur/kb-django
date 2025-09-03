# apps/sales_team_management/views/comisiones.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.http import JsonResponse
from django import forms
import json
from ..decorators_modules import commissions_module_required

# NUEVO MODELO - Sin Legacy
from ..models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)
from ..forms import CommissionStructureForm
from apps.real_estate_projects.models import (
    Proyecto, ComisionDesarrollo
)


# ============================================================
# FORMS PARA COMISIONES - Se usan desde forms.py
# ============================================================


# ============================================================
# VISTAS PARA COMISIONES USANDO NUEVO MODELO
# ============================================================

@login_required
@permission_required('real_estate_projects.change_proyecto', raise_exception=True)
def comisiones_desarrollo_config(request, proyecto_pk):
    """Configurar comisiones de desarrollo para un proyecto (mantener funcionalidad original)"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)

    try:
        comision = proyecto.comision_desarrollo
    except ComisionDesarrollo.DoesNotExist:
        comision = None

    if request.method == 'POST':
        # Usar form original para ComisionDesarrollo
        from ..forms import ComisionDesarrolloForm
        form = ComisionDesarrolloForm(request.POST, instance=comision)
        if form.is_valid():
            comision = form.save(commit=False)
            comision.proyecto = proyecto
            comision.save()
            messages.success(request, 'Comisiones de desarrollo configuradas exitosamente.')
            return redirect('real_estate_projects:proyectos_detail', pk=proyecto.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        from ..forms import ComisionDesarrolloForm
        form = ComisionDesarrolloForm(instance=comision)

    context = {
        'form': form,
        'proyecto': proyecto,
        'comision': comision,
        'title': f'Comisiones de Desarrollo - {proyecto.nombre}',
        'action': 'Configurar' if not comision else 'Actualizar'
    }
    return render(request, 'sales_team_management/comisiones/desarrollo_form.html', context)


@login_required
@permission_required('sales_team_management.change_commissionstructure', raise_exception=True)
def comisiones_equipo_config(request, unit_id):
    """Configurar estructura de comisiones para una unidad organizacional"""
    unit = get_object_or_404(OrganizationalUnit, id=unit_id, is_active=True)

    # Obtener estructura existente o crear nueva
    commission_structure = CommissionStructure.objects.filter(
        organizational_unit=unit,
        is_active=True
    ).first()

    if request.method == 'POST':
        form = CommissionStructureForm(
            request.POST, 
            instance=commission_structure,
            organizational_unit=unit
        )
        if form.is_valid():
            structure = form.save(commit=False)
            structure.organizational_unit = unit
            structure.save()
            messages.success(request, 'Estructura de comisiones configurada exitosamente.')
            return redirect('sales_team_management:equipo_detail', equipo_id=unit.id)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = CommissionStructureForm(
            instance=commission_structure,
            organizational_unit=unit
        )

    context = {
        'form': form,
        'unit': unit,
        'commission_structure': commission_structure,
        'title': f'Comisiones - {unit.name}',
        'action': 'Configurar' if not commission_structure else 'Actualizar'
    }
    return render(request, 'sales_team_management/comisiones/equipo_form.html', context)


# ============================================================
# VISTAS PRINCIPALES DE GESTIÓN DE COMISIONES
# ============================================================

from ..decorators import team_management_permission_required

@login_required
@commissions_module_required
def comisiones_equipos_list(request):
    """Lista de unidades organizacionales para gestión de comisiones"""
    
    # Filtros
    search = request.GET.get('search', '')
    unit_type_filter = request.GET.get('unit_type', '')
    estado_comision = request.GET.get('estado_comision', 'todos')
    
    # Query base
    units = OrganizationalUnit.objects.filter(is_active=True)
    
    # Aplicar filtros
    if search:
        units = units.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(code__icontains=search)
        )
    
    if unit_type_filter:
        units = units.filter(unit_type=unit_type_filter)
    
    if estado_comision == 'configurado':
        units = units.filter(commissionsstructure__is_active=True)
    elif estado_comision == 'pendiente':
        units = units.filter(
            Q(commissionsstructure__isnull=True) |
            Q(commissionsstructure__is_active=False)
        )
    
    # Agregar información de comisiones y miembros
    units = units.annotate(
        total_members=Count('teammembership', filter=Q(teammembership__is_active=True)),
        commission_structures_count=Count('commissionsstructure', filter=Q(commissionsstructure__is_active=True))
    ).order_by('name')
    
    # Paginación
    paginator = Paginator(units, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas para filtros
    total_units = OrganizationalUnit.objects.filter(is_active=True).count()
    units_configuradas = OrganizationalUnit.objects.filter(
        is_active=True,
        commissionsstructure__is_active=True
    ).distinct().count()
    units_pendientes = total_units - units_configuradas
    
    # Tipos de unidad para filtros
    unit_types = OrganizationalUnit.UNIT_TYPES
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'unit_type_filter': unit_type_filter,
        'estado_comision': estado_comision,
        'unit_types': unit_types,
        'stats': {
            'total': total_units,
            'configuradas': units_configuradas,
            'pendientes': units_pendientes,
        },
        'title': 'Comisiones de Unidades Organizacionales',
    }
    
    return render(request, 'sales_team_management/comisiones/equipos_list.html', context)


@login_required
@permission_required('real_estate_projects.view_proyecto', raise_exception=True)
def comisiones_proyectos_list(request):
    """Lista de proyectos para gestión de comisiones de desarrollo"""
    
    # Filtros
    search = request.GET.get('search', '')
    estado_comision = request.GET.get('estado_comision', 'todos')
    
    # Query base
    proyectos = Proyecto.objects.filter(activo=True)
    
    # Aplicar filtros
    if search:
        proyectos = proyectos.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if estado_comision == 'configurado':
        proyectos = proyectos.filter(comision_desarrollo__isnull=False)
    elif estado_comision == 'pendiente':
        proyectos = proyectos.filter(comision_desarrollo__isnull=True)
    
    # Agregar información de comisiones
    proyectos = proyectos.select_related('comision_desarrollo').order_by('nombre')
    
    # Paginación
    paginator = Paginator(proyectos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas para filtros
    total_proyectos = Proyecto.objects.filter(activo=True).count()
    proyectos_configurados = Proyecto.objects.filter(
        activo=True, comision_desarrollo__isnull=False
    ).count()
    proyectos_pendientes = total_proyectos - proyectos_configurados
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'estado_comision': estado_comision,
        'stats': {
            'total': total_proyectos,
            'configurados': proyectos_configurados,
            'pendientes': proyectos_pendientes,
        },
        'title': 'Comisiones de Proyectos de Desarrollo',
    }
    
    return render(request, 'sales_team_management/comisiones/proyectos_list.html', context)


@login_required
@permission_required('sales_team_management.view_commissionstructure', raise_exception=True)
def comision_structure_detail(request, structure_id):
    """Detalle de una estructura de comisiones"""
    
    structure = get_object_or_404(CommissionStructure, id=structure_id, is_active=True)
    unit = structure.organizational_unit
    
    # Obtener membresías activas del equipo
    memberships = TeamMembership.objects.filter(
        organizational_unit=unit,
        is_active=True
    ).select_related('user', 'position_type').order_by('position_type__hierarchy_level')
    
    # Calcular distribución de comisiones
    position_distribution = []
    for position_code, percentage in structure.position_percentages.items():
        try:
            position = PositionType.objects.get(code=position_code, is_active=True)
            members_count = memberships.filter(position_type=position).count()
            position_distribution.append({
                'position': position,
                'percentage': percentage,
                'members_count': members_count,
                'individual_percentage': percentage / members_count if members_count > 0 else 0
            })
        except PositionType.DoesNotExist:
            continue
    
    context = {
        'structure': structure,
        'unit': unit,
        'memberships': memberships,
        'position_distribution': position_distribution,
        'title': f'Estructura de Comisiones - {unit.name}'
    }
    
    return render(request, 'sales_team_management/comisiones/structure_detail.html', context)


# ============================================================
# VISTAS AJAX
# ============================================================

@login_required
def get_commission_structure_json(request, unit_id):
    """API para obtener estructura de comisiones en JSON"""
    
    unit = get_object_or_404(OrganizationalUnit, id=unit_id)
    
    structure = CommissionStructure.objects.filter(
        organizational_unit=unit,
        is_active=True
    ).first()
    
    if not structure:
        return JsonResponse({
            'success': False,
            'message': 'No hay estructura de comisiones configurada'
        })
    
    return JsonResponse({
        'success': True,
        'structure': {
            'id': structure.id,
            'name': structure.structure_name,
            'commission_type': structure.commission_type,
            'position_percentages': structure.position_percentages,
            'created_at': structure.created_at.isoformat(),
            'updated_at': structure.updated_at.isoformat()
        }
    })