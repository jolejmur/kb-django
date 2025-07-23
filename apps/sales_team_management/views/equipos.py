# apps/sales_team_management/views/equipos.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from django import forms
import json

from ..models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    ComisionVenta
)
from apps.real_estate_projects.models import (
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    AsignacionEquipoProyecto, ComisionDesarrollo
)
from ..forms import (
    EquipoVentaForm, GerenteEquipoForm, MiembroEquipoForm, ProyectoForm, InmuebleForm,
    ComisionDesarrolloForm, ComisionVentaForm, EquipoVentaFilterForm,
    ProyectoFilterForm
)


# ============================================================
# VISTAS DE EQUIPOS DE VENTA
# ============================================================

@login_required
@permission_required('sales_team_management.view_equipoventa', raise_exception=True)
def equipos_venta_list(request):
    """Lista todos los equipos de venta con filtros"""
    form = EquipoVentaFilterForm(request.GET)
    equipos = EquipoVenta.objects.annotate(
        total_gerentes=Count('gerenteequipo', filter=Q(gerenteequipo__activo=True))
    ).select_related().order_by('nombre')

    # Aplicar filtros
    if form.is_valid():
        nombre = form.cleaned_data.get('nombre')
        activo = form.cleaned_data.get('activo')

        if nombre:
            equipos = equipos.filter(nombre__icontains=nombre)

        if activo == 'true':
            equipos = equipos.filter(activo=True)
        elif activo == 'false':
            equipos = equipos.filter(activo=False)

    # Paginación
    paginator = Paginator(equipos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_form': form,
        'title': 'Equipos de Venta',
    }
    return render(request, 'sales_team_management/equipos/list.html', context)


@login_required
@permission_required('sales_team_management.view_equipoventa', raise_exception=True)
def equipos_venta_detail(request, pk):
    """Ver detalles de un equipo de venta"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)
    gerentes = equipo.gerentes_equipo

    # Estadísticas del equipo
    total_jefes = sum(gerente.jefeventas.count() for gerente in gerentes.all())
    
    stats = {
        'total_gerentes': gerentes.count(),
        'total_jefes': total_jefes,
        'total_vendedores': equipo.total_vendedores,
        'proyectos_asignados': equipo.proyectos.filter(
            asignacionequipoproyecto__activo=True
        ).count(),
    }

    context = {
        'equipo': equipo,
        'gerentes': gerentes,
        'stats': stats,
        'title': f'Equipo: {equipo.nombre}',
    }
    return render(request, 'sales_team_management/equipos/detail.html', context)


@login_required
@permission_required('sales_team_management.add_equipoventa', raise_exception=True)
def equipos_venta_create(request):
    """Crear un nuevo equipo de venta"""
    if request.method == 'POST':
        form = EquipoVentaForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            messages.success(request, f'Equipo de venta "{equipo.nombre}" creado exitosamente.')
            return redirect('sales:equipos_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = EquipoVentaForm()

    context = {
        'form': form,
        'title': 'Crear Equipo de Venta',
        'action': 'Crear',
        'help_text': 'Un equipo de venta agrupa vendedores bajo una estructura jerárquica.'
    }
    return render(request, 'sales_team_management/equipos/form.html', context)


@login_required
@permission_required('sales_team_management.change_equipoventa', raise_exception=True)
def equipos_venta_edit(request, pk):
    """Editar un equipo de venta existente"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)

    if request.method == 'POST':
        form = EquipoVentaForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Equipo de venta "{equipo.nombre}" actualizado exitosamente.')
            return redirect('sales:equipos_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = EquipoVentaForm(instance=equipo)

    context = {
        'form': form,
        'equipo': equipo,
        'title': f'Editar Equipo: {equipo.nombre}',
        'action': 'Actualizar'
    }
    return render(request, 'sales_team_management/equipos/form.html', context)


@login_required
@permission_required('sales_team_management.delete_equipoventa', raise_exception=True)
def equipos_venta_delete(request, pk):
    """Eliminar un equipo de venta"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)

    # Verificar si el equipo puede ser eliminado antes de mostrar el formulario
    if not equipo.can_be_deleted():
        blockers = equipo.get_deletion_blockers()
        blockers_text = ", ".join(blockers)
        messages.error(
            request,
            f'No se puede eliminar el equipo "{equipo.nombre}" porque tiene: {blockers_text}. '
            f'Primero desactiva o reasigna estos elementos.'
        )
        return redirect('sales:equipos_list')

    if request.method == 'POST':
        try:
            if not equipo.can_be_deleted():
                blockers = equipo.get_deletion_blockers()
                blockers_text = ", ".join(blockers)
                messages.error(
                    request,
                    f'No se puede eliminar el equipo "{equipo.nombre}" porque tiene: {blockers_text}. '
                    f'Primero desactiva o reasigna estos elementos.'
                )
                return redirect('sales:equipos_list')

            equipo_nombre = equipo.nombre
            equipo.delete()
            messages.success(request, f'Equipo "{equipo_nombre}" eliminado exitosamente.')
            return redirect('sales:equipos_list')

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('sales:equipos_list')

    context = {
        'equipo': equipo,
        'title': f'Eliminar Equipo: {equipo.nombre}',
    }
    return render(request, 'sales_team_management/equipos/delete.html', context)


@login_required
@permission_required('sales_team_management.change_equipoventa', raise_exception=True)
def equipos_manage_hierarchy(request, pk):
    """Gestionar la jerarquía de un equipo de ventas"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)

    # Filtros
    mostrar_inactivos = request.GET.get('mostrar_inactivos', '').lower() == 'true'
    filtro_rol = request.GET.get('rol', 'todos')

    # Obtener toda la jerarquía
    gerentes_query = equipo.gerenteequipo_set.select_related('usuario')
    if mostrar_inactivos:
        gerentes_query = gerentes_query.filter(activo=False)
    else:
        gerentes_query = gerentes_query.filter(activo=True)

    gerentes = gerentes_query.all()
    hierarchy_data = []

    # Estadísticas
    stats = {
        'total_gerentes': equipo.gerenteequipo_set.filter(activo=True).count(),
        'total_jefes': 0,
        'total_leaders': 0,
        'total_vendedores': 0,
    }

    for gerente in gerentes:
        gerente_data = {
            'gerente': gerente,
            'jefes_venta': []
        }

        jefes_query = gerente.jefeventas.select_related('usuario')
        if mostrar_inactivos:
            jefes_query = jefes_query.filter(activo=False)
        else:
            jefes_query = jefes_query.filter(activo=True)
        
        jefes = jefes_query.all()
        stats['total_jefes'] += jefes.count()

        for jefe in jefes:
            jefe_data = {
                'jefe': jefe,
                'team_leaders': []
            }

            team_leaders_query = jefe.teamleaders.select_related('usuario')
            if mostrar_inactivos:
                team_leaders_query = team_leaders_query.filter(activo=False)
            else:
                team_leaders_query = team_leaders_query.filter(activo=True)
            
            team_leaders = team_leaders_query.all()
            stats['total_leaders'] += team_leaders.count()

            for tl in team_leaders:
                vendedores_query = tl.vendedores.select_related('usuario')
                if mostrar_inactivos:
                    vendedores_query = vendedores_query.filter(activo=False)
                else:
                    vendedores_query = vendedores_query.filter(activo=True)
                
                vendedores = vendedores_query.all()
                stats['total_vendedores'] += vendedores.count()

                tl_data = {
                    'team_leader': tl,
                    'vendedores': vendedores
                }
                jefe_data['team_leaders'].append(tl_data)

            gerente_data['jefes_venta'].append(jefe_data)

        hierarchy_data.append(gerente_data)

    # Aplicar filtro por rol si es necesario
    if filtro_rol != 'todos':
        # Esta lógica se puede implementar más tarde si es necesario
        pass

    # Estadísticas adicionales
    stats['total_miembros'] = (
        stats['total_gerentes'] + 
        stats['total_jefes'] + 
        stats['total_leaders'] + 
        stats['total_vendedores']
    )

    # Verificar si tiene gerentes activos
    tiene_gerente_activo = equipo.gerenteequipo_set.filter(activo=True).exists()

    # Obtener equipos disponibles para migración (activos y diferentes al actual)
    equipos_disponibles = EquipoVenta.objects.filter(activo=True).exclude(id=equipo.id).order_by('nombre')

    context = {
        'equipo': equipo,
        'hierarchy_data': hierarchy_data,
        'stats': stats,
        'mostrar_inactivos': mostrar_inactivos,
        'filtro_rol': filtro_rol,
        'tiene_gerente_activo': tiene_gerente_activo,
        'equipos_disponibles': equipos_disponibles,
        'title': f'Jerarquía - {equipo.nombre}',
    }
    return render(request, 'sales_team_management/equipos/hierarchy.html', context)


@login_required
@permission_required('sales_team_management.add_gerenteequipo', raise_exception=True)
def equipos_add_gerente(request, pk):
    """Agregar gerente a un equipo"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)

    if request.method == 'POST':
        form = GerenteEquipoForm(request.POST)
        if form.is_valid():
            gerente = form.save(commit=False)
            gerente.equipo_venta = equipo
            gerente.save()
            messages.success(request, f'Gerente "{gerente.usuario.get_full_name()}" agregado exitosamente.')
            return redirect('sales:equipos_hierarchy', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = GerenteEquipoForm()
        form.fields['equipo_venta'].initial = equipo
        form.fields['equipo_venta'].widget = forms.HiddenInput()

    # Verificar si tiene gerentes activos
    tiene_gerente_activo = equipo.gerenteequipo_set.filter(activo=True).exists()

    context = {
        'form': form,
        'equipo': equipo,
        'tiene_gerente_activo': tiene_gerente_activo,
        'title': f'Agregar Gerente - {equipo.nombre}',
        'action': 'Agregar'
    }
    return render(request, 'sales_team_management/equipos/add_gerente.html', context)


@login_required
@permission_required('sales_team_management.change_equipoventa', raise_exception=True)
def equipos_add_member(request, pk):
    """Agregar miembro del equipo con rol unificado"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)
    
    if request.method == 'POST':
        form = MiembroEquipoForm(request.POST, equipo=equipo)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            rol = form.cleaned_data['rol']
            supervisor = form.cleaned_data.get('supervisor')
            
            try:
                # Crear el registro según el rol seleccionado
                if rol == 'gerente':
                    GerenteEquipo.objects.create(
                        usuario=usuario,
                        equipo_venta=equipo,
                        activo=True
                    )
                    messages.success(request, f'Gerente "{usuario.get_full_name()}" agregado exitosamente.')
                
                elif rol == 'jefe_venta':
                    # Buscar el gerente supervisor
                    gerente_supervisor = equipo.gerenteequipo_set.filter(
                        usuario=supervisor, activo=True
                    ).first()
                    if not gerente_supervisor:
                        messages.error(request, 'No se encontró el gerente supervisor.')
                        return redirect('sales:equipos_hierarchy', pk=equipo.pk)
                    
                    JefeVenta.objects.create(
                        usuario=usuario,
                        gerente_equipo=gerente_supervisor,
                        activo=True
                    )
                    messages.success(request, f'Jefe de Venta "{usuario.get_full_name()}" agregado exitosamente.')
                
                elif rol == 'team_leader':
                    # Buscar el jefe de venta supervisor
                    jefe_supervisor = None
                    for gerente in equipo.gerenteequipo_set.filter(activo=True):
                        jefe_supervisor = gerente.jefeventas.filter(
                            usuario=supervisor, activo=True
                        ).first()
                        if jefe_supervisor:
                            break
                    
                    if not jefe_supervisor:
                        messages.error(request, 'No se encontró el jefe de venta supervisor.')
                        return redirect('sales:equipos_hierarchy', pk=equipo.pk)
                    
                    TeamLeader.objects.create(
                        usuario=usuario,
                        jefe_venta=jefe_supervisor,
                        activo=True
                    )
                    messages.success(request, f'Team Leader "{usuario.get_full_name()}" agregado exitosamente.')
                
                elif rol == 'vendedor':
                    # Buscar el team leader supervisor
                    team_leader_supervisor = None
                    for gerente in equipo.gerenteequipo_set.filter(activo=True):
                        for jefe in gerente.jefeventas.filter(activo=True):
                            team_leader_supervisor = jefe.teamleaders.filter(
                                usuario=supervisor, activo=True
                            ).first()
                            if team_leader_supervisor:
                                break
                        if team_leader_supervisor:
                            break
                    
                    if not team_leader_supervisor:
                        messages.error(request, 'No se encontró el team leader supervisor.')
                        return redirect('sales:equipos_hierarchy', pk=equipo.pk)
                    
                    Vendedor.objects.create(
                        usuario=usuario,
                        team_leader=team_leader_supervisor,
                        activo=True
                    )
                    messages.success(request, f'Vendedor "{usuario.get_full_name()}" agregado exitosamente.')
                
                return redirect('sales:equipos_hierarchy', pk=equipo.pk)
                
            except Exception as e:
                messages.error(request, f'Error al agregar el miembro: {str(e)}')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = MiembroEquipoForm(equipo=equipo)
    
    # Calcular estadísticas del equipo
    stats = {
        'total_gerentes': equipo.gerenteequipo_set.filter(activo=True).count(),
        'total_jefes': 0,
        'total_leaders': 0,
        'total_vendedores': 0,
    }

    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        jefes_activos = gerente.jefeventas.filter(activo=True)
        stats['total_jefes'] += jefes_activos.count()
        
        for jefe in jefes_activos:
            team_leaders_activos = jefe.teamleaders.filter(activo=True)
            stats['total_leaders'] += team_leaders_activos.count()
            
            for team_leader in team_leaders_activos:
                stats['total_vendedores'] += team_leader.vendedores.filter(activo=True).count()
    
    # Obtener supervisores disponibles según el rol seleccionado
    supervisores_data = {}
    
    # Gerentes disponibles para jefes de venta
    supervisores_data['gerentes'] = []
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        supervisores_data['gerentes'].append({
            'id': gerente.usuario.id,
            'name': gerente.usuario.get_full_name() or gerente.usuario.username
        })
    
    # Jefes de venta disponibles para team leaders
    supervisores_data['jefes_venta'] = []
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        for jefe in gerente.jefeventas.filter(activo=True):
            supervisores_data['jefes_venta'].append({
                'id': jefe.usuario.id,
                'name': jefe.usuario.get_full_name() or jefe.usuario.username
            })
    
    # Team leaders disponibles para vendedores
    supervisores_data['team_leaders'] = []
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        for jefe in gerente.jefeventas.filter(activo=True):
            for leader in jefe.teamleaders.filter(activo=True):
                supervisores_data['team_leaders'].append({
                    'id': leader.usuario.id,
                    'name': leader.usuario.get_full_name() or leader.usuario.username
                })
    
    # Verificar si tiene gerentes activos
    tiene_gerente_activo = equipo.gerenteequipo_set.filter(activo=True).exists()

    context = {
        'form': form,
        'equipo': equipo,
        'stats': stats,
        'tiene_gerente_activo': tiene_gerente_activo,
        'supervisores_data': json.dumps(supervisores_data),
        'title': f'Agregar Miembro - {equipo.nombre}',
        'help_text': 'Selecciona el usuario y su rol en la jerarquía del equipo.'
    }
    return render(request, 'sales_team_management/equipos/add_member.html', context)


