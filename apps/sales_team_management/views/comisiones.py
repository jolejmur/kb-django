# apps/sales_team_management/views/comisiones.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import (
    EquipoVenta, ComisionVenta
)
from apps.real_estate_projects.models import (
    Proyecto, ComisionDesarrollo
)
from ..forms import (
    ComisionDesarrolloForm, ComisionVentaForm
)


# ============================================================
# VISTAS PARA COMISIONES
# ============================================================

@login_required
@permission_required('real_estate_projects.change_proyecto', raise_exception=True)
def comisiones_desarrollo_config(request, proyecto_pk):
    """Configurar comisiones de desarrollo para un proyecto"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)

    try:
        comision = proyecto.comision_desarrollo
    except ComisionDesarrollo.DoesNotExist:
        comision = None

    if request.method == 'POST':
        form = ComisionDesarrolloForm(request.POST, instance=comision)
        if form.is_valid():
            comision = form.save(commit=False)
            comision.proyecto = proyecto
            comision.save()
            messages.success(request, 'Comisiones de desarrollo configuradas exitosamente.')
            return redirect('sales:proyectos_detail', pk=proyecto.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
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
@permission_required('sales_team_management.change_equipoventa', raise_exception=True)
def comisiones_venta_config(request, equipo_pk):
    """Configurar comisiones de venta para un equipo"""
    equipo = get_object_or_404(EquipoVenta, pk=equipo_pk)

    try:
        comision = equipo.comision_venta
    except ComisionVenta.DoesNotExist:
        comision = None

    if request.method == 'POST':
        form = ComisionVentaForm(request.POST, instance=comision)
        if form.is_valid():
            comision = form.save(commit=False)
            comision.equipo_venta = equipo
            comision.save()
            messages.success(request, 'Comisiones de venta configuradas exitosamente.')
            return redirect('sales:equipos_detail', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ComisionVentaForm(instance=comision)

    context = {
        'form': form,
        'equipo': equipo,
        'comision': comision,
        'title': f'Comisiones de Venta - {equipo.nombre}',
        'action': 'Configurar' if not comision else 'Actualizar'
    }
    return render(request, 'sales_team_management/comisiones/venta_form.html', context)


# ============================================================
# VISTAS PRINCIPALES DE GESTIÓN DE COMISIONES
# ============================================================


@login_required
@permission_required('sales_team_management.view_equipoventa', raise_exception=True)
def comisiones_equipos_list(request):
    """Lista de equipos para gestión de comisiones"""
    
    # Filtros
    search = request.GET.get('search', '')
    estado_comision = request.GET.get('estado_comision', 'todos')
    
    # Query base
    equipos = EquipoVenta.objects.filter(activo=True)
    
    # Aplicar filtros
    if search:
        equipos = equipos.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    if estado_comision == 'configurado':
        equipos = equipos.filter(comision_venta__isnull=False)
    elif estado_comision == 'pendiente':
        equipos = equipos.filter(comision_venta__isnull=True)
    
    # Agregar información de comisiones
    equipos = equipos.select_related('comision_venta').order_by('nombre')
    
    # Paginación
    paginator = Paginator(equipos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas para filtros
    total_equipos = EquipoVenta.objects.filter(activo=True).count()
    equipos_configurados = EquipoVenta.objects.filter(
        activo=True, comision_venta__isnull=False
    ).count()
    equipos_pendientes = total_equipos - equipos_configurados
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'estado_comision': estado_comision,
        'stats': {
            'total': total_equipos,
            'configurados': equipos_configurados,
            'pendientes': equipos_pendientes,
        },
        'title': 'Comisiones de Equipos de Venta',
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