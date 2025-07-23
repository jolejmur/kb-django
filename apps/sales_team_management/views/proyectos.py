# apps/sales_team_management/views/proyectos.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum, Min, Max
from django.core.exceptions import ValidationError

from apps.real_estate_projects.models import (
    Proyecto, ComisionDesarrollo, AsignacionEquipoProyecto
)
from ..forms import ProyectoForm, ProyectoFilterForm


@login_required
@permission_required('real_estate_projects.view_proyecto', raise_exception=True)
def proyectos_list(request):
    """Lista todos los proyectos con filtros"""
    form = ProyectoFilterForm(request.GET)
    proyectos = Proyecto.objects.select_related(
        'gerente_proyecto__usuario',
        'jefe_proyecto__usuario'
    ).annotate(
        total_inmuebles=Count('inmuebles'),
        inmuebles_vendidos=Count('inmuebles', filter=Q(inmuebles__estado='vendido')),
        equipos_asignados=Count('equipos_venta', filter=Q(asignacionequipoproyecto__activo=True))
    ).order_by('-created_at')

    # Aplicar filtros
    if form.is_valid():
        nombre = form.cleaned_data.get('nombre')
        estado = form.cleaned_data.get('estado')
        gerente_proyecto = form.cleaned_data.get('gerente_proyecto')
        activo = form.cleaned_data.get('activo')

        if nombre:
            proyectos = proyectos.filter(nombre__icontains=nombre)

        if estado:
            proyectos = proyectos.filter(estado=estado)

        if gerente_proyecto:
            proyectos = proyectos.filter(gerente_proyecto=gerente_proyecto)

        if activo == 'true':
            proyectos = proyectos.filter(activo=True)
        elif activo == 'false':
            proyectos = proyectos.filter(activo=False)

    # Paginación
    paginator = Paginator(proyectos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_form': form,
        'title': 'Proyectos',
    }
    return render(request, 'sales_team_management/proyectos/list.html', context)


@login_required
@permission_required('real_estate_projects.view_proyecto', raise_exception=True)
def proyectos_detail(request, pk):
    """Ver detalles de un proyecto"""
    proyecto = get_object_or_404(Proyecto.objects.select_related(
        'gerente_proyecto__usuario',
        'jefe_proyecto__usuario'
    ).prefetch_related('inmuebles', 'equipos_venta'), pk=pk)

    # Estadísticas del proyecto
    inmuebles = proyecto.inmuebles.all()
    stats = {
        'total_inmuebles': inmuebles.count(),
        'inmuebles_disponibles': inmuebles.filter(disponible=True, estado='disponible').count(),
        'inmuebles_reservados': inmuebles.filter(estado='reservado').count(),
        'inmuebles_vendidos': inmuebles.filter(estado='vendido').count(),
        'inmuebles_bloqueados': inmuebles.filter(estado='bloqueado').count(),
    }

    if stats['total_inmuebles'] > 0:
        stats['porcentaje_vendido'] = round(
            (stats['inmuebles_vendidos'] / stats['total_inmuebles']) * 100, 2
        )
    else:
        stats['porcentaje_vendido'] = 0

    # Rangos de precios de inmuebles
    if inmuebles.exists():
        precio_stats = inmuebles.aggregate(
            precio_min=Min('precio_venta'),
            precio_max=Max('precio_venta'),
            precio_promedio=Avg('precio_venta')
        )
        stats.update(precio_stats)

    # Equipos asignados
    equipos_asignados = proyecto.equipos_venta.filter(
        asignacionequipoproyecto__activo=True
    )

    # Comisiones de desarrollo
    try:
        comision_desarrollo = proyecto.comision_desarrollo
    except ComisionDesarrollo.DoesNotExist:
        comision_desarrollo = None

    context = {
        'proyecto': proyecto,
        'stats': stats,
        'equipos_asignados': equipos_asignados,
        'comision_desarrollo': comision_desarrollo,
        'title': f'Proyecto: {proyecto.nombre}',
    }
    return render(request, 'sales_team_management/proyectos/detail.html', context)


@login_required
@permission_required('real_estate_projects.add_proyecto', raise_exception=True)
def proyectos_create(request):
    """Crear un nuevo proyecto"""
    if request.method == 'POST':
        form = ProyectoForm(request.POST)
        if form.is_valid():
            proyecto = form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" creado exitosamente.')
            return redirect('sales:proyectos_detail', pk=proyecto.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ProyectoForm()

    context = {
        'form': form,
        'title': 'Crear Proyecto',
        'action': 'Crear',
        'help_text': 'Un proyecto agrupa inmuebles bajo una gestión de desarrollo y venta específica.'
    }
    return render(request, 'sales_team_management/proyectos/form.html', context)


@login_required
@permission_required('real_estate_projects.change_proyecto', raise_exception=True)
def proyectos_edit(request, pk):
    """Editar un proyecto existente"""
    proyecto = get_object_or_404(Proyecto, pk=pk)

    if request.method == 'POST':
        form = ProyectoForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" actualizado exitosamente.')
            return redirect('sales:proyectos_detail', pk=proyecto.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ProyectoForm(instance=proyecto)

    context = {
        'form': form,
        'proyecto': proyecto,
        'title': f'Editar Proyecto: {proyecto.nombre}',
        'action': 'Actualizar'
    }
    return render(request, 'sales_team_management/proyectos/form.html', context)


@login_required
@permission_required('real_estate_projects.delete_proyecto', raise_exception=True)
def proyectos_delete(request, pk):
    """Eliminar un proyecto"""
    proyecto = get_object_or_404(Proyecto, pk=pk)

    if request.method == 'POST':
        try:
            if not proyecto.can_be_deleted():
                messages.error(
                    request,
                    f'No se puede eliminar el proyecto "{proyecto.nombre}" porque tiene inmuebles o procesos de venta asociados.'
                )
                return redirect('sales:proyectos_list')

            proyecto_nombre = proyecto.nombre
            proyecto.delete()
            messages.success(request, f'Proyecto "{proyecto_nombre}" eliminado exitosamente.')
            return redirect('sales:proyectos_list')

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('sales:proyectos_list')

    # Información para mostrar en la confirmación
    inmuebles_count = proyecto.inmuebles.count()
    equipos_count = proyecto.equipos_venta.filter(
        asignacionequipoproyecto__activo=True
    ).count()

    context = {
        'proyecto': proyecto,
        'inmuebles_count': inmuebles_count,
        'equipos_count': equipos_count,
        'title': f'Eliminar Proyecto: {proyecto.nombre}',
    }
    return render(request, 'sales_team_management/proyectos/delete.html', context)