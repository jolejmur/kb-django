# apps/sales_team_management/views/inmuebles.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator

from apps.real_estate_projects.models import Proyecto, Inmueble
from ..forms import InmuebleForm


# ============================================================
# VISTAS PARA INMUEBLES
# ============================================================

@login_required
@permission_required('real_estate_projects.view_inmueble', raise_exception=True)
def inmuebles_list(request, proyecto_pk):
    """Lista inmuebles de un proyecto específico"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)
    inmuebles = proyecto.inmuebles.all().order_by('codigo')

    # Filtros básicos
    estado = request.GET.get('estado')
    tipo = request.GET.get('tipo')
    disponible = request.GET.get('disponible')

    if estado:
        inmuebles = inmuebles.filter(estado=estado)
    if tipo:
        inmuebles = inmuebles.filter(tipo=tipo)
    if disponible == 'true':
        inmuebles = inmuebles.filter(disponible=True)
    elif disponible == 'false':
        inmuebles = inmuebles.filter(disponible=False)

    # Paginación
    paginator = Paginator(inmuebles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Estadísticas
    stats = {
        'total': inmuebles.count(),
        'disponibles': inmuebles.filter(disponible=True, estado='disponible').count(),
        'reservados': inmuebles.filter(estado='reservado').count(),
        'vendidos': inmuebles.filter(estado='vendido').count(),
    }

    context = {
        'proyecto': proyecto,
        'page_obj': page_obj,
        'stats': stats,
        'current_filters': {
            'estado': estado,
            'tipo': tipo,
            'disponible': disponible,
        },
        'title': f'Inmuebles - {proyecto.nombre}',
    }
    return render(request, 'sales_team_management/inmuebles/list.html', context)


@login_required
@permission_required('real_estate_projects.view_inmueble', raise_exception=True)
def inmuebles_detail(request, proyecto_pk, pk):
    """Ver detalles de un inmueble"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)
    inmueble = get_object_or_404(Inmueble, pk=pk, proyecto=proyecto)

    context = {
        'proyecto': proyecto,
        'inmueble': inmueble,
        'title': f'Inmueble: {inmueble.codigo}',
    }
    return render(request, 'sales_team_management/inmuebles/detail.html', context)


@login_required
@permission_required('real_estate_projects.add_inmueble', raise_exception=True)
def inmuebles_create(request, proyecto_pk):
    """Crear un nuevo inmueble en un proyecto"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)

    if request.method == 'POST':
        form = InmuebleForm(request.POST)
        if form.is_valid():
            inmueble = form.save(commit=False)
            inmueble.proyecto = proyecto
            inmueble.save()
            messages.success(request, f'Inmueble "{inmueble.codigo}" creado exitosamente.')
            return redirect('sales:inmuebles_detail', proyecto_pk=proyecto.pk, pk=inmueble.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = InmuebleForm()

    context = {
        'form': form,
        'proyecto': proyecto,
        'title': f'Crear Inmueble - {proyecto.nombre}',
        'action': 'Crear'
    }
    return render(request, 'sales_team_management/inmuebles/form.html', context)


@login_required
@permission_required('real_estate_projects.change_inmueble', raise_exception=True)
def inmuebles_edit(request, proyecto_pk, pk):
    """Editar un inmueble existente"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)
    inmueble = get_object_or_404(Inmueble, pk=pk, proyecto=proyecto)

    if request.method == 'POST':
        form = InmuebleForm(request.POST, instance=inmueble)
        if form.is_valid():
            form.save()
            messages.success(request, f'Inmueble "{inmueble.codigo}" actualizado exitosamente.')
            return redirect('sales:inmuebles_detail', proyecto_pk=proyecto.pk, pk=inmueble.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = InmuebleForm(instance=inmueble)

    context = {
        'form': form,
        'proyecto': proyecto,
        'inmueble': inmueble,
        'title': f'Editar Inmueble: {inmueble.codigo}',
        'action': 'Actualizar'
    }
    return render(request, 'sales_team_management/inmuebles/form.html', context)


@login_required
@permission_required('real_estate_projects.delete_inmueble', raise_exception=True)
def inmuebles_delete(request, proyecto_pk, pk):
    """Eliminar un inmueble"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)
    inmueble = get_object_or_404(Inmueble, pk=pk, proyecto=proyecto)

    if request.method == 'POST':
        codigo = inmueble.codigo
        inmueble.delete()
        messages.success(request, f'Inmueble "{codigo}" eliminado exitosamente.')
        return redirect('sales:inmuebles_list', proyecto_pk=proyecto.pk)

    context = {
        'proyecto': proyecto,
        'inmueble': inmueble,
        'title': f'Eliminar Inmueble: {inmueble.codigo}',
    }
    return render(request, 'sales_team_management/inmuebles/delete.html', context)