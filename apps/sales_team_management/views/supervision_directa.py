# apps/sales_team_management/views/supervision_directa.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import get_user_model

from ..models import SupervisionDirecta, EquipoVenta
from ..forms import SupervisionDirectaForm

User = get_user_model()


@login_required
@permission_required('sales_team_management.view_supervisiondirecta', raise_exception=True)
def supervision_directa_list(request):
    """Lista todas las supervisiones directas"""
    
    # Filtros de búsqueda
    search_query = request.GET.get('search', '')
    equipo_filter = request.GET.get('equipo', '')
    tipo_filter = request.GET.get('tipo', '')
    estado_filter = request.GET.get('estado', '')
    
    # Query base
    supervisiones = SupervisionDirecta.objects.select_related(
        'supervisor', 'subordinado', 'equipo_venta'
    ).order_by('-fecha_inicio')
    
    # Aplicar filtros
    if search_query:
        supervisiones = supervisiones.filter(
            Q(supervisor__first_name__icontains=search_query) |
            Q(supervisor__last_name__icontains=search_query) |
            Q(supervisor__username__icontains=search_query) |
            Q(subordinado__first_name__icontains=search_query) |
            Q(subordinado__last_name__icontains=search_query) |
            Q(subordinado__username__icontains=search_query)
        )
    
    if equipo_filter:
        supervisiones = supervisiones.filter(equipo_venta_id=equipo_filter)
    
    if tipo_filter:
        supervisiones = supervisiones.filter(tipo_supervision=tipo_filter)
    
    if estado_filter == 'activo':
        supervisiones = supervisiones.filter(activo=True)
    elif estado_filter == 'inactivo':
        supervisiones = supervisiones.filter(activo=False)
    
    # Paginación
    paginator = Paginator(supervisiones, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    equipos = EquipoVenta.objects.filter(activo=True).order_by('nombre')
    tipos_supervision = SupervisionDirecta.TIPOS_SUPERVISION
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'equipo_filter': equipo_filter,
        'tipo_filter': tipo_filter,
        'estado_filter': estado_filter,
        'equipos': equipos,
        'tipos_supervision': tipos_supervision,
        'title': 'Supervisiones Directas'
    }
    
    return render(request, 'sales_team_management/supervision_directa/list.html', context)


@login_required
@permission_required('sales_team_management.add_supervisiondirecta', raise_exception=True)
def supervision_directa_create(request):
    """Crear nueva supervisión directa"""
    
    equipo_id = request.GET.get('equipo')
    equipo = None
    if equipo_id:
        equipo = get_object_or_404(EquipoVenta, id=equipo_id, activo=True)
    
    if request.method == 'POST':
        form = SupervisionDirectaForm(request.POST, equipo=equipo)
        if form.is_valid():
            supervision = form.save()
            messages.success(
                request, 
                f'Supervisión directa creada: {supervision.supervisor.get_full_name()} → {supervision.subordinado.get_full_name()}'
            )
            return redirect('sales:supervision_directa_list')
    else:
        form = SupervisionDirectaForm(equipo=equipo)
    
    context = {
        'form': form,
        'title': 'Crear Supervisión Directa',
        'action': 'Crear',
        'equipo': equipo
    }
    
    return render(request, 'sales_team_management/supervision_directa/form.html', context)


@login_required
@permission_required('sales_team_management.change_supervisiondirecta', raise_exception=True)
def supervision_directa_edit(request, pk):
    """Editar supervisión directa"""
    
    supervision = get_object_or_404(SupervisionDirecta, pk=pk)
    
    if request.method == 'POST':
        form = SupervisionDirectaForm(request.POST, instance=supervision, equipo=supervision.equipo_venta)
        if form.is_valid():
            supervision = form.save()
            messages.success(
                request, 
                f'Supervisión directa actualizada: {supervision.supervisor.get_full_name()} → {supervision.subordinado.get_full_name()}'
            )
            return redirect('sales:supervision_directa_list')
    else:
        form = SupervisionDirectaForm(instance=supervision, equipo=supervision.equipo_venta)
    
    context = {
        'form': form,
        'supervision': supervision,
        'title': 'Editar Supervisión Directa',
        'action': 'Actualizar'
    }
    
    return render(request, 'sales_team_management/supervision_directa/form.html', context)


@login_required
@permission_required('sales_team_management.view_supervisiondirecta', raise_exception=True)
def supervision_directa_detail(request, pk):
    """Ver detalles de supervisión directa"""
    
    supervision = get_object_or_404(
        SupervisionDirecta.objects.select_related(
            'supervisor', 'subordinado', 'equipo_venta'
        ), 
        pk=pk
    )
    
    context = {
        'supervision': supervision,
        'title': f'Supervisión Directa: {supervision.supervisor.get_full_name()} → {supervision.subordinado.get_full_name()}'
    }
    
    return render(request, 'sales_team_management/supervision_directa/detail.html', context)


@login_required
@permission_required('sales_team_management.change_supervisiondirecta', raise_exception=True)
@require_http_methods(["POST"])
def supervision_directa_toggle(request, pk):
    """Activar/desactivar supervisión directa"""
    
    supervision = get_object_or_404(SupervisionDirecta, pk=pk)
    
    if supervision.activo:
        supervision.desactivar()
        messages.success(request, f'Supervisión directa desactivada: {supervision}')
    else:
        # Validar que no haya otra supervisión activa para el mismo subordinado en el mismo equipo
        supervision_existente = SupervisionDirecta.objects.filter(
            subordinado=supervision.subordinado,
            equipo_venta=supervision.equipo_venta,
            activo=True
        ).exclude(pk=supervision.pk).first()
        
        if supervision_existente:
            messages.error(
                request, 
                f'No se puede activar: {supervision.subordinado.get_full_name()} ya tiene supervisión directa activa con {supervision_existente.supervisor.get_full_name()}'
            )
        else:
            supervision.activo = True
            supervision.fecha_fin = None
            supervision.save()
            messages.success(request, f'Supervisión directa activada: {supervision}')
    
    return redirect('sales:supervision_directa_list')


@login_required
@permission_required('sales_team_management.delete_supervisiondirecta', raise_exception=True)
def supervision_directa_delete(request, pk):
    """Eliminar supervisión directa"""
    
    supervision = get_object_or_404(SupervisionDirecta, pk=pk)
    
    if request.method == 'POST':
        supervisor_name = supervision.supervisor.get_full_name()
        subordinado_name = supervision.subordinado.get_full_name()
        supervision.delete()
        
        messages.success(
            request, 
            f'Supervisión directa eliminada: {supervisor_name} → {subordinado_name}'
        )
        return redirect('sales:supervision_directa_list')
    
    context = {
        'supervision': supervision,
        'title': 'Confirmar Eliminación'
    }
    
    return render(request, 'sales_team_management/supervision_directa/delete.html', context)


# ============================================================
# VISTAS AJAX PARA SUPERVISIÓN DIRECTA
# ============================================================

@login_required
@require_http_methods(["GET"])
def ajax_supervisores_disponibles(request):
    """AJAX: Obtiene supervisores disponibles para un equipo"""
    
    equipo_id = request.GET.get('equipo_id')
    if not equipo_id:
        return JsonResponse({'error': 'ID de equipo requerido'}, status=400)
    
    try:
        equipo = EquipoVenta.objects.get(id=equipo_id, activo=True)
    except EquipoVenta.DoesNotExist:
        return JsonResponse({'error': 'Equipo no encontrado'}, status=404)
    
    supervisores = []
    
    # Gerentes del equipo
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        supervisores.append({
            'id': gerente.usuario.id,
            'nombre': gerente.usuario.get_full_name() or gerente.usuario.username,
            'rol': 'Gerente de Equipo'
        })
    
    # Jefes de venta del equipo
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        for jefe in gerente.jefeventas.filter(activo=True):
            supervisores.append({
                'id': jefe.usuario.id,
                'nombre': jefe.usuario.get_full_name() or jefe.usuario.username,
                'rol': 'Jefe de Venta'
            })
    
    return JsonResponse({'supervisores': supervisores})


@login_required
@require_http_methods(["GET"])
def ajax_subordinados_disponibles(request):
    """AJAX: Obtiene subordinados disponibles para un equipo"""
    
    equipo_id = request.GET.get('equipo_id')
    if not equipo_id:
        return JsonResponse({'error': 'ID de equipo requerido'}, status=400)
    
    try:
        equipo = EquipoVenta.objects.get(id=equipo_id, activo=True)
    except EquipoVenta.DoesNotExist:
        return JsonResponse({'error': 'Equipo no encontrado'}, status=404)
    
    subordinados = []
    
    # Team Leaders del equipo
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        for jefe in gerente.jefeventas.filter(activo=True):
            for team_leader in jefe.teamleaders.filter(activo=True):
                subordinados.append({
                    'id': team_leader.usuario.id,
                    'nombre': team_leader.usuario.get_full_name() or team_leader.usuario.username,
                    'rol': 'Team Leader'
                })
                
                # Vendedores del equipo
                for vendedor in team_leader.vendedores.filter(activo=True):
                    subordinados.append({
                        'id': vendedor.usuario.id,
                        'nombre': vendedor.usuario.get_full_name() or vendedor.usuario.username,
                        'rol': 'Vendedor'
                    })
    
    return JsonResponse({'subordinados': subordinados})


@login_required
@require_http_methods(["GET"])
def ajax_validar_tipo_supervision(request):
    """AJAX: Valida si un tipo de supervisión es válido para supervisor-subordinado específicos"""
    
    supervisor_id = request.GET.get('supervisor_id')
    subordinado_id = request.GET.get('subordinado_id')
    equipo_id = request.GET.get('equipo_id')
    
    if not all([supervisor_id, subordinado_id, equipo_id]):
        return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
    
    try:
        supervisor = User.objects.get(id=supervisor_id)
        subordinado = User.objects.get(id=subordinado_id)
        equipo = EquipoVenta.objects.get(id=equipo_id, activo=True)
    except (User.DoesNotExist, EquipoVenta.DoesNotExist):
        return JsonResponse({'error': 'Usuario o equipo no encontrado'}, status=404)
    
    # Determinar roles
    supervisor_rol = _get_rol_usuario_en_equipo(supervisor, equipo)
    subordinado_rol = _get_rol_usuario_en_equipo(subordinado, equipo)
    
    # Tipos válidos según combinación de roles
    tipos_validos = []
    
    if supervisor_rol == 'GERENTE' and subordinado_rol == 'VENDEDOR':
        tipos_validos.append(('GERENTE_TO_VENDEDOR', 'Gerente supervisa Vendedor directamente'))
    
    if supervisor_rol == 'GERENTE' and subordinado_rol == 'TEAM_LEADER':
        tipos_validos.append(('GERENTE_TO_TEAMLEADER', 'Gerente supervisa Team Leader directamente'))
    
    if supervisor_rol == 'JEFE_VENTA' and subordinado_rol == 'VENDEDOR':
        tipos_validos.append(('JEFE_TO_VENDEDOR', 'Jefe Venta supervisa Vendedor directamente'))
    
    return JsonResponse({
        'tipos_validos': tipos_validos,
        'supervisor_rol': supervisor_rol,
        'subordinado_rol': subordinado_rol
    })


def _get_rol_usuario_en_equipo(usuario, equipo):
    """Helper: Obtiene el rol de un usuario en un equipo específico"""
    
    # Buscar en gerentes
    if equipo.gerenteequipo_set.filter(usuario=usuario, activo=True).exists():
        return 'GERENTE'
    
    # Buscar en jefes de venta
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        if gerente.jefeventas.filter(usuario=usuario, activo=True).exists():
            return 'JEFE_VENTA'
    
    # Buscar en team leaders
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        for jefe in gerente.jefeventas.filter(activo=True):
            if jefe.teamleaders.filter(usuario=usuario, activo=True).exists():
                return 'TEAM_LEADER'
    
    # Buscar en vendedores
    for gerente in equipo.gerenteequipo_set.filter(activo=True):
        for jefe in gerente.jefeventas.filter(activo=True):
            for team_leader in jefe.teamleaders.filter(activo=True):
                if team_leader.vendedores.filter(usuario=usuario, activo=True).exists():
                    return 'VENDEDOR'
    
    return 'DESCONOCIDO'