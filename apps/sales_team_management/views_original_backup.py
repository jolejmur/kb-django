# apps/sales/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from django import forms

from .models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    ComisionDesarrollo, ComisionVenta, AsignacionEquipoProyecto
)
from .forms import (
    EquipoVentaForm, GerenteEquipoForm, MiembroEquipoForm, ProyectoForm, InmuebleForm,
    ComisionDesarrolloForm, ComisionVentaForm, EquipoVentaFilterForm,
    ProyectoFilterForm
)


# ============================================================
# FUNCIONES HELPER
# ============================================================

def get_member_by_role(member_id, rol):
    """
    Función helper para obtener un miembro según su rol
    Retorna: (miembro_actual, usuario, equipo_actual)
    """
    from django.contrib.auth.models import User
    
    try:
        if rol == 'gerente':
            miembro_actual = GerenteEquipo.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.equipo_venta
        elif rol == 'jefe':
            miembro_actual = JefeVenta.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.gerente_equipo.equipo_venta
        elif rol == 'team_leader':
            miembro_actual = TeamLeader.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.jefe_venta.gerente_equipo.equipo_venta
        elif rol == 'vendedor':
            miembro_actual = Vendedor.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.team_leader.jefe_venta.gerente_equipo.equipo_venta
        else:
            return None, None, None
        
        return miembro_actual, usuario, equipo_actual
        
    except (GerenteEquipo.DoesNotExist, JefeVenta.DoesNotExist, 
            TeamLeader.DoesNotExist, Vendedor.DoesNotExist):
        return None, None, None


# ============================================================
# VISTAS PARA EQUIPOS DE VENTA
# ============================================================

@login_required
@permission_required('sales.view_equipoventa', raise_exception=True)
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
    return render(request, 'sales/equipos/list.html', context)


@login_required
@permission_required('sales.view_equipoventa', raise_exception=True)
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
    return render(request, 'sales/equipos/detail.html', context)


@login_required
@permission_required('sales.add_equipoventa', raise_exception=True)
def equipos_venta_create(request):
    """Crear un nuevo equipo de venta"""
    if request.method == 'POST':
        form = EquipoVentaForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            messages.success(request, f'Equipo de venta "{equipo.nombre}" creado exitosamente.')
            return redirect('sales:equipos_detail', pk=equipo.pk)
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
    return render(request, 'sales/equipos/form.html', context)


@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
def equipos_venta_edit(request, pk):
    """Editar un equipo de venta existente"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)

    if request.method == 'POST':
        form = EquipoVentaForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Equipo de venta "{equipo.nombre}" actualizado exitosamente.')
            return redirect('sales:equipos_detail', pk=equipo.pk)
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
    return render(request, 'sales/equipos/form.html', context)


@login_required
@permission_required('sales.delete_equipoventa', raise_exception=True)
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
    return render(request, 'sales/equipos/delete.html', context)


# ============================================================
# VISTA PARA JERARQUÍA DE EQUIPOS
# ============================================================

@login_required
@permission_required('sales.view_equipoventa', raise_exception=True)
def jerarquia_equipos_list(request):
    """Lista de jerarquía de equipos con filtros por equipo y rol"""
    
    # Filtros
    equipo_id = request.GET.get('equipo')
    rol = request.GET.get('rol')
    activo = request.GET.get('activo')
    search = request.GET.get('search', '').strip()
    
    
    # Lista para almacenar todos los miembros
    miembros = []
    
    # Obtener todos los equipos para el filtro
    equipos = EquipoVenta.objects.filter(activo=True).order_by('nombre')
    
    # Filtrar equipos si se especifica
    equipos_filtrados = equipos
    if equipo_id:
        try:
            equipo_id = int(equipo_id)
            equipos_filtrados = equipos_filtrados.filter(id=equipo_id)
        except (ValueError, TypeError):
            pass
    
    # Recopilar todos los miembros de todos los equipos
    for equipo in equipos_filtrados:
        # Gerentes
        for gerente in equipo.gerenteequipo_set.all():
            if activo and activo != 'todos':
                if (activo == 'true' and not gerente.activo) or (activo == 'false' and gerente.activo):
                    continue
            
            if rol and rol != 'todos' and rol != 'gerente':
                continue
                
            usuario = gerente.usuario
            nombre_completo = usuario.get_full_name() or ""
            
            # Verificar si este gerente coincide con la búsqueda
            gerente_matches_search = True
            if search:
                search_lower = search.lower()
                nombre_lower = nombre_completo.lower()
                username_lower = usuario.username.lower()
                email_lower = (usuario.email or "").lower()
                gerente_matches_search = (search_lower in nombre_lower or search_lower in username_lower or search_lower in email_lower)
            
            # Si el gerente coincide con la búsqueda, agregarlo a los resultados
            if gerente_matches_search:
                # Verificar si puede eliminar (no tiene subalternos)
                puede_eliminar = not gerente.jefeventas.exists()
                
                miembros.append({
                    'equipo': equipo,
                    'usuario': usuario,
                    'rol': 'Gerente de Equipo',
                    'rol_key': 'gerente',
                    'activo': gerente.activo,
                    'fecha_asignacion': gerente.created_at,
                    'supervisor': None,
                    'objeto': gerente,
                    'puede_eliminar': puede_eliminar
                })
            
            # Jefes de Venta bajo este gerente
            for jefe in gerente.jefeventas.all():
                if activo and activo != 'todos':
                    if (activo == 'true' and not jefe.activo) or (activo == 'false' and jefe.activo):
                        continue
                
                if rol and rol != 'todos' and rol != 'jefe':
                    continue
                    
                usuario_jefe = jefe.usuario
                nombre_completo_jefe = usuario_jefe.get_full_name() or ""
                
                # Verificar si este jefe coincide con la búsqueda
                jefe_matches_search = True
                if search:
                    search_lower = search.lower()
                    jefe_matches_search = (search_lower in nombre_completo_jefe.lower() or search_lower in usuario_jefe.username.lower() or search_lower in (usuario_jefe.email or "").lower())
                
                # Si el jefe coincide con la búsqueda, agregarlo a los resultados
                if jefe_matches_search:
                    # Verificar si puede eliminar (no tiene subalternos)
                    puede_eliminar_jefe = not jefe.teamleaders.exists()
                    
                    miembros.append({
                        'equipo': equipo,
                        'usuario': usuario_jefe,
                        'rol': 'Jefe de Venta',
                        'rol_key': 'jefe',
                        'activo': jefe.activo,
                        'fecha_asignacion': jefe.created_at,
                        'supervisor': usuario.get_full_name() or usuario.username,
                        'objeto': jefe,
                        'puede_eliminar': puede_eliminar_jefe
                    })
                
                # Team Leaders bajo este jefe
                for team_leader in jefe.teamleaders.all():
                    if activo and activo != 'todos':
                        if (activo == 'true' and not team_leader.activo) or (activo == 'false' and team_leader.activo):
                            continue
                    
                    if rol and rol != 'todos' and rol != 'team_leader':
                        continue
                        
                    usuario_tl = team_leader.usuario
                    nombre_completo_tl = usuario_tl.get_full_name() or ""
                    
                    # Verificar si este team leader coincide con la búsqueda
                    tl_matches_search = True
                    if search:
                        search_lower = search.lower()
                        tl_matches_search = (search_lower in nombre_completo_tl.lower() or search_lower in usuario_tl.username.lower() or search_lower in (usuario_tl.email or "").lower())
                    
                    # Si el team leader coincide con la búsqueda, agregarlo a los resultados
                    if tl_matches_search:
                        # Verificar si puede eliminar (no tiene subalternos)
                        puede_eliminar_tl = not team_leader.vendedores.exists()
                        
                        miembros.append({
                            'equipo': equipo,
                            'usuario': usuario_tl,
                            'rol': 'Team Leader',
                            'rol_key': 'team_leader',
                            'activo': team_leader.activo,
                            'fecha_asignacion': team_leader.created_at,
                            'supervisor': usuario_jefe.get_full_name() or usuario_jefe.username,
                            'objeto': team_leader,
                            'puede_eliminar': puede_eliminar_tl
                        })
                    
                    # Vendedores bajo este team leader
                    for vendedor in team_leader.vendedores.all():
                        if activo and activo != 'todos':
                            if (activo == 'true' and not vendedor.activo) or (activo == 'false' and vendedor.activo):
                                continue
                        
                        if rol and rol != 'todos' and rol != 'vendedor':
                            continue
                            
                        usuario_v = vendedor.usuario
                        nombre_completo_v = usuario_v.get_full_name() or ""
                        
                        # Verificar si este vendedor coincide con la búsqueda
                        vendedor_matches_search = True
                        if search:
                            search_lower = search.lower()
                            vendedor_matches_search = (search_lower in nombre_completo_v.lower() or search_lower in usuario_v.username.lower() or search_lower in (usuario_v.email or "").lower())
                        
                        # Si el vendedor coincide con la búsqueda, agregarlo a los resultados
                        if vendedor_matches_search:
                            # Para vendedores verificar que no tenga procesos de venta vigentes
                            # TODO: Aquí necesitarías verificar si tiene procesos de venta vigentes
                            # Por ahora asumo que puede eliminar, pero debes implementar la verificación
                            puede_eliminar_v = True  # Cambiar por la lógica real de procesos de venta
                            
                            miembros.append({
                                'equipo': equipo,
                                'usuario': usuario_v,
                                'rol': 'Vendedor',
                                'rol_key': 'vendedor',
                                'activo': vendedor.activo,
                                'fecha_asignacion': vendedor.created_at,
                                'supervisor': usuario_tl.get_full_name() or usuario_tl.username,
                                'objeto': vendedor,
                                'puede_eliminar': puede_eliminar_v
                            })
    
    # Ordenar por equipo, luego por rol, luego por nombre
    orden_roles = {'gerente': 1, 'jefe': 2, 'team_leader': 3, 'vendedor': 4}
    miembros.sort(key=lambda x: (
        x['equipo'].nombre,
        orden_roles.get(x['rol_key'], 5),
        x['usuario'].get_full_name() or x['usuario'].username
    ))
    
    # Calcular estadísticas correctas
    stats = {
        'total_miembros': len(miembros),
        'total_gerentes': len([m for m in miembros if m['rol_key'] == 'gerente' and m['activo']]),
        'total_jefes': len([m for m in miembros if m['rol_key'] == 'jefe' and m['activo']]),
        'total_team_leaders': len([m for m in miembros if m['rol_key'] == 'team_leader' and m['activo']]),
        'total_vendedores': len([m for m in miembros if m['rol_key'] == 'vendedor' and m['activo']]),
    }
    
    # Paginación con opciones de entradas por página
    page_size = request.GET.get('page_size', '25')
    try:
        page_size = int(page_size)
        if page_size not in [10, 25, 50, 100]:
            page_size = 25
    except (ValueError, TypeError):
        page_size = 25
    
    paginator = Paginator(miembros, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'equipos': equipos,
        'equipo_seleccionado': equipo_id,
        'rol_seleccionado': rol,
        'activo_seleccionado': activo,
        'search': search,
        'stats': stats,
        'page_size': page_size,
        'page_size_options': [10, 25, 50, 100],
        'title': 'Jerarquía de Equipos',
    }
    return render(request, 'sales/jerarquia/list.html', context)


@login_required
@permission_required('sales.add_equipoventa', raise_exception=True)
def jerarquia_create_member(request):
    """Crear/asignar un nuevo miembro a la jerarquía"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario')
        equipo_id = request.POST.get('equipo')
        rol = request.POST.get('rol')
        supervisor_id = request.POST.get('supervisor')
        
        try:
            usuario = User.objects.get(id=usuario_id)
            equipo = EquipoVenta.objects.get(id=equipo_id)
            
            # Validar que el usuario no esté ya asignado en este equipo
            if rol == 'gerente':
                if GerenteEquipo.objects.filter(usuario=usuario, equipo_venta=equipo).exists():
                    messages.error(request, f'{usuario.get_full_name() or usuario.username} ya es gerente de este equipo.')
                    return redirect('sales:jerarquia_create_member')
                
                # Verificar si ya hay un gerente activo en el equipo
                gerente_actual = GerenteEquipo.objects.filter(equipo_venta=equipo, activo=True).first()
                if gerente_actual:
                    # Verificar si el usuario confirmó el reemplazo
                    confirmar_reemplazo = request.POST.get('confirmar_reemplazo')
                    if not confirmar_reemplazo:
                        # Mostrar advertencia y pedir confirmación
                        context = {
                            'equipo': equipo,
                            'usuario_nuevo': usuario,
                            'gerente_actual': gerente_actual,
                            'rol': rol,
                            'requiere_confirmacion': True,
                            'title': 'Confirmar Reemplazo de Gerente',
                        }
                        return render(request, 'sales/jerarquia/confirm_replace.html', context)
                    
                    # Usuario confirmó, transferir jefes de venta y desactivar gerente actual
                    jefes_de_venta = gerente_actual.jefeventas.filter(activo=True)
                    
                    # Crear el nuevo gerente primero
                    nuevo_gerente = GerenteEquipo.objects.create(usuario=usuario, equipo_venta=equipo)
                    
                    # Transferir todos los jefes de venta al nuevo gerente
                    jefes_transferidos = 0
                    for jefe in jefes_de_venta:
                        jefe.gerente_equipo = nuevo_gerente
                        jefe.save()
                        jefes_transferidos += 1
                    
                    # Desactivar gerente actual
                    gerente_actual.activo = False
                    gerente_actual.save()
                    
                    messages.warning(request, f'Gerente anterior ({gerente_actual.usuario.get_full_name() or gerente_actual.usuario.username}) desactivado.')
                    if jefes_transferidos > 0:
                        messages.info(request, f'{jefes_transferidos} jefe(s) de venta transferido(s) al nuevo gerente.')
                    
                    messages.success(request, f'{usuario.get_full_name() or usuario.username} asignado como Gerente de Equipo en {equipo.nombre}.')
                    return redirect('sales:jerarquia_list')
                
                # Si no hay gerente actual, crear directamente
                GerenteEquipo.objects.create(usuario=usuario, equipo_venta=equipo)
                messages.success(request, f'{usuario.get_full_name() or usuario.username} asignado como Gerente de Equipo en {equipo.nombre}.')
                
            elif rol == 'jefe':
                supervisor = GerenteEquipo.objects.get(id=supervisor_id)
                if JefeVenta.objects.filter(usuario=usuario, gerente_equipo=supervisor).exists():
                    messages.error(request, f'{usuario.get_full_name() or usuario.username} ya es jefe de venta bajo este gerente.')
                    return redirect('sales:jerarquia_create_member')
                
                JefeVenta.objects.create(usuario=usuario, gerente_equipo=supervisor)
                messages.success(request, f'{usuario.get_full_name() or usuario.username} asignado como Jefe de Venta.')
                
            elif rol == 'team_leader':
                supervisor = JefeVenta.objects.get(id=supervisor_id)
                if TeamLeader.objects.filter(usuario=usuario, jefe_venta=supervisor).exists():
                    messages.error(request, f'{usuario.get_full_name() or usuario.username} ya es team leader bajo este jefe.')
                    return redirect('sales:jerarquia_create_member')
                
                TeamLeader.objects.create(usuario=usuario, jefe_venta=supervisor)
                messages.success(request, f'{usuario.get_full_name() or usuario.username} asignado como Team Leader.')
                
            elif rol == 'vendedor':
                supervisor = TeamLeader.objects.get(id=supervisor_id)
                if Vendedor.objects.filter(usuario=usuario, team_leader=supervisor).exists():
                    messages.error(request, f'{usuario.get_full_name() or usuario.username} ya es vendedor bajo este team leader.')
                    return redirect('sales:jerarquia_create_member')
                
                Vendedor.objects.create(usuario=usuario, team_leader=supervisor)
                messages.success(request, f'{usuario.get_full_name() or usuario.username} asignado como Vendedor.')
            
            return redirect('sales:jerarquia_list')
            
        except Exception as e:
            messages.error(request, f'Error al asignar usuario: {str(e)}')
            return redirect('sales:jerarquia_create_member')
    
    # GET request - mostrar formulario
    equipos = EquipoVenta.objects.filter(activo=True).order_by('nombre')
    
    # Obtener usuarios que NO tienen asignación en ningún equipo
    usuarios_con_asignacion = set()
    
    # Usuarios que son gerentes
    usuarios_con_asignacion.update(
        GerenteEquipo.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    # Usuarios que son jefes de venta
    usuarios_con_asignacion.update(
        JefeVenta.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    # Usuarios que son team leaders
    usuarios_con_asignacion.update(
        TeamLeader.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    # Usuarios que son vendedores
    usuarios_con_asignacion.update(
        Vendedor.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    
    # Filtrar usuarios sin asignación
    usuarios_disponibles = User.objects.filter(
        is_active=True
    ).exclude(
        id__in=usuarios_con_asignacion
    ).order_by('first_name', 'last_name', 'username')
    
    context = {
        'equipos': equipos,
        'usuarios': usuarios_disponibles,
        'title': 'Asignar Usuario a Equipo',
    }
    return render(request, 'sales/jerarquia/create.html', context)


@login_required
@permission_required('sales.view_equipoventa', raise_exception=True)
def jerarquia_member_detail(request, member_id, rol):
    """Ver detalles de un miembro de la jerarquía"""
    from datetime import datetime, date
    from django.db.models import Sum, Count
    
    try:
        # Obtener el objeto según el rol
        if rol == 'gerente':
            miembro = get_object_or_404(GerenteEquipo, id=member_id)
            equipo = miembro.equipo_venta
            usuario = miembro.usuario
            rol_display = 'Gerente de Equipo'
            supervisor = None
        elif rol == 'jefe':
            miembro = get_object_or_404(JefeVenta, id=member_id)
            equipo = miembro.gerente_equipo.equipo_venta
            usuario = miembro.usuario
            rol_display = 'Jefe de Venta'
            supervisor = miembro.gerente_equipo.usuario
        elif rol == 'team_leader':
            miembro = get_object_or_404(TeamLeader, id=member_id)
            equipo = miembro.jefe_venta.gerente_equipo.equipo_venta
            usuario = miembro.usuario
            rol_display = 'Team Leader'
            supervisor = miembro.jefe_venta.usuario
        elif rol == 'vendedor':
            miembro = get_object_or_404(Vendedor, id=member_id)
            equipo = miembro.team_leader.jefe_venta.gerente_equipo.equipo_venta
            usuario = miembro.usuario
            rol_display = 'Vendedor'
            supervisor = miembro.team_leader.usuario
        else:
            messages.error(request, 'Rol no válido.')
            return redirect('sales:jerarquia_list')
        
        # Calcular estadísticas del mes actual
        hoy = date.today()
        primer_dia_mes = hoy.replace(day=1)
        
        # Estadísticas básicas (preparadas para cuando se implementen las ventas)
        estadisticas_mes = {
            'ventas_cerradas': 0,  # TODO: Implementar cuando tengas modelo de ventas
            'monto_vendido': 0,    # TODO: Implementar cuando tengas modelo de ventas
            'comisiones': 0,       # TODO: Implementar cuando tengas modelo de comisiones
            'leads_asignados': 0,  # TODO: Implementar cuando tengas modelo de leads
            'conversion_rate': 0,  # TODO: Calcular porcentaje de conversión
        }
        
        # Estadísticas de equipo
        if rol == 'gerente':
            subordinados_count = miembro.jefeventas.filter(activo=True).count()
            subordinados_tipo = 'Jefes de Venta'
        elif rol == 'jefe':
            subordinados_count = miembro.teamleaders.filter(activo=True).count()
            subordinados_tipo = 'Team Leaders'
        elif rol == 'team_leader':
            subordinados_count = miembro.vendedores.filter(activo=True).count()
            subordinados_tipo = 'Vendedores'
        else:
            subordinados_count = 0
            subordinados_tipo = None
        
        context = {
            'miembro': miembro,
            'usuario': usuario,
            'equipo': equipo,
            'rol': rol,
            'rol_display': rol_display,
            'supervisor': supervisor,
            'estadisticas_mes': estadisticas_mes,
            'subordinados_count': subordinados_count,
            'subordinados_tipo': subordinados_tipo,
            'mes_actual': hoy.strftime('%B %Y'),
            'title': f'{rol_display}: {usuario.get_full_name() or usuario.username}',
        }
        
        return render(request, 'sales/jerarquia/detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar detalles: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
def jerarquia_member_edit(request, member_id, rol):
    """Editar un miembro de la jerarquía (incluyendo cambio de equipo)"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Obtener el objeto según el rol
        if rol == 'gerente':
            miembro = get_object_or_404(GerenteEquipo, id=member_id)
            equipo_actual = miembro.equipo_venta
        elif rol == 'jefe':
            miembro = get_object_or_404(JefeVenta, id=member_id)
            equipo_actual = miembro.gerente_equipo.equipo_venta
        elif rol == 'team_leader':
            miembro = get_object_or_404(TeamLeader, id=member_id)
            equipo_actual = miembro.jefe_venta.gerente_equipo.equipo_venta
        elif rol == 'vendedor':
            miembro = get_object_or_404(Vendedor, id=member_id)
            equipo_actual = miembro.team_leader.jefe_venta.gerente_equipo.equipo_venta
        else:
            messages.error(request, 'Rol no válido.')
            return redirect('sales:jerarquia_list')
        
        if request.method == 'POST':
            nuevo_equipo_id = request.POST.get('equipo')
            nuevo_supervisor_id = request.POST.get('supervisor')
            activo = request.POST.get('activo') == 'on'
            accion = request.POST.get('accion', 'editar')  # 'editar' o 'inactivar'
            reemplazo_id = request.POST.get('reemplazo')
            
            # Verificar si se está intentando inactivar un usuario con subordinados
            if miembro.activo and not activo and rol != 'vendedor':
                # Verificar si tiene subordinados
                has_subordinados = False
                subordinados_info = []
                
                if rol == 'gerente':
                    subordinados = miembro.jefeventas.filter(activo=True)
                    has_subordinados = subordinados.exists()
                    for subordinado in subordinados:
                        subordinados_info.append({
                            'nombre': subordinado.usuario.get_full_name() or subordinado.usuario.username,
                            'rol': 'Jefe de Venta'
                        })
                elif rol == 'jefe':
                    subordinados = miembro.teamleaders.filter(activo=True)
                    has_subordinados = subordinados.exists()
                    for subordinado in subordinados:
                        subordinados_info.append({
                            'nombre': subordinado.usuario.get_full_name() or subordinado.usuario.username,
                            'rol': 'Team Leader'
                        })
                elif rol == 'team_leader':
                    subordinados = miembro.vendedores.filter(activo=True)
                    has_subordinados = subordinados.exists()
                    for subordinado in subordinados:
                        subordinados_info.append({
                            'nombre': subordinado.usuario.get_full_name() or subordinado.usuario.username,
                            'rol': 'Vendedor'
                        })
                
                if has_subordinados:
                    if not reemplazo_id:
                        # Redirigir al diálogo de inactivación con reemplazo
                        messages.warning(
                            request,
                            f'{miembro.usuario.get_full_name() or miembro.usuario.username} tiene subordinados asignados. '
                            f'Debes seleccionar un reemplazo antes de inactivarlo.'
                        )
                        return redirect('sales:jerarquia_member_deactivate', member_id=member_id, rol=rol)
                    else:
                        # Procesar reemplazo
                        try:
                            from django.contrib.auth.models import User
                            if reemplazo_id.startswith('user_'):
                                # Es un usuario sin equipo
                                user_id = reemplazo_id.replace('user_', '')
                                reemplazo_usuario = User.objects.get(id=user_id)
                                
                                if rol == 'gerente':
                                    nuevo_gerente = GerenteEquipo.objects.create(
                                        usuario=reemplazo_usuario, 
                                        equipo_venta=equipo_actual
                                    )
                                    subordinados = miembro.jefeventas.filter(activo=True)
                                    for subordinado in subordinados:
                                        subordinado.gerente_equipo = nuevo_gerente
                                        subordinado.save()
                                elif rol == 'jefe':
                                    nuevo_jefe = JefeVenta.objects.create(
                                        usuario=reemplazo_usuario,
                                        gerente_equipo=miembro.gerente_equipo
                                    )
                                    subordinados = miembro.teamleaders.filter(activo=True)
                                    for subordinado in subordinados:
                                        subordinado.jefe_venta = nuevo_jefe
                                        subordinado.save()
                                elif rol == 'team_leader':
                                    nuevo_tl = TeamLeader.objects.create(
                                        usuario=reemplazo_usuario,
                                        jefe_venta=miembro.jefe_venta
                                    )
                                    subordinados = miembro.vendedores.filter(activo=True)
                                    for subordinado in subordinados:
                                        subordinado.team_leader = nuevo_tl
                                        subordinado.save()
                                        
                            else:
                                # Es un miembro existente inactivo - reactivarlo
                                if rol == 'gerente':
                                    reemplazo_gerente = GerenteEquipo.objects.get(id=reemplazo_id)
                                    reemplazo_gerente.activo = True
                                    reemplazo_gerente.save()
                                    subordinados = miembro.jefeventas.filter(activo=True)
                                    for subordinado in subordinados:
                                        subordinado.gerente_equipo = reemplazo_gerente
                                        subordinado.save()
                                elif rol == 'jefe':
                                    reemplazo_jefe = JefeVenta.objects.get(id=reemplazo_id)
                                    reemplazo_jefe.activo = True
                                    reemplazo_jefe.save()
                                    subordinados = miembro.teamleaders.filter(activo=True)
                                    for subordinado in subordinados:
                                        subordinado.jefe_venta = reemplazo_jefe
                                        subordinado.save()
                                elif rol == 'team_leader':
                                    reemplazo_tl = TeamLeader.objects.get(id=reemplazo_id)
                                    reemplazo_tl.activo = True
                                    reemplazo_tl.save()
                                    subordinados = miembro.vendedores.filter(activo=True)
                                    for subordinado in subordinados:
                                        subordinado.team_leader = reemplazo_tl
                                        subordinado.save()
                            
                            messages.success(
                                request,
                                f'Subordinados transferidos exitosamente al reemplazo.'
                            )
                            
                        except Exception as e:
                            messages.error(request, f'Error al transferir subordinados: {str(e)}')
                            return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
            
            # Manejar inactivación con subordinados
            if accion == 'inactivar' and miembro.activo:
                # Verificar si tiene subordinados
                tiene_subordinados = False
                subordinados_info = []
                
                if rol == 'gerente':
                    subordinados = miembro.jefeventas.filter(activo=True)
                    if subordinados.exists():
                        tiene_subordinados = True
                        subordinados_info = [f"{s.usuario.get_full_name() or s.usuario.username} (Jefe de Venta)" for s in subordinados]
                elif rol == 'jefe':
                    subordinados = miembro.teamleaders.filter(activo=True)
                    if subordinados.exists():
                        tiene_subordinados = True
                        subordinados_info = [f"{s.usuario.get_full_name() or s.usuario.username} (Team Leader)" for s in subordinados]
                elif rol == 'team_leader':
                    subordinados = miembro.vendedores.filter(activo=True)
                    if subordinados.exists():
                        tiene_subordinados = True
                        subordinados_info = [f"{s.usuario.get_full_name() or s.usuario.username} (Vendedor)" for s in subordinados]
                
                if tiene_subordinados:
                    # Obtener posibles reemplazos
                    posibles_reemplazos = []
                    if rol == 'gerente':
                        # Para gerentes, buscar otros gerentes inactivos en cualquier equipo
                        reemplazos = GerenteEquipo.objects.filter(activo=False).exclude(id=miembro.id)
                        posibles_reemplazos = [{'id': r.id, 'nombre': f"{r.usuario.get_full_name() or r.usuario.username} - {r.equipo_venta.nombre}", 'tipo': 'gerente'} for r in reemplazos]
                    elif rol == 'jefe':
                        # Para jefes, buscar otros jefes inactivos del mismo equipo
                        reemplazos = JefeVenta.objects.filter(gerente_equipo__equipo_venta=equipo_actual, activo=False).exclude(id=miembro.id)
                        posibles_reemplazos = [{'id': r.id, 'nombre': f"{r.usuario.get_full_name() or r.usuario.username}", 'tipo': 'jefe'} for r in reemplazos]
                    elif rol == 'team_leader':
                        # Para team leaders, buscar otros team leaders inactivos del mismo equipo
                        reemplazos = TeamLeader.objects.filter(jefe_venta__gerente_equipo__equipo_venta=equipo_actual, activo=False).exclude(id=miembro.id)
                        posibles_reemplazos = [{'id': r.id, 'nombre': f"{r.usuario.get_full_name() or r.usuario.username}", 'tipo': 'team_leader'} for r in reemplazos]
                    
                    # Mostrar diálogo de reemplazo
                    context = {
                        'miembro': miembro,
                        'usuario': miembro.usuario,
                        'rol': rol,
                        'rol_display': rol.replace('_', ' ').title(),
                        'equipo_actual': equipo_actual,
                        'subordinados_info': subordinados_info,
                        'posibles_reemplazos': posibles_reemplazos,
                        'title': f'Confirmar Inactivación de {rol.replace("_", " ").title()}',
                        'requiere_reemplazo': True,
                    }
                    return render(request, 'sales/jerarquia/confirm_inactivate.html', context)
                
                # Si no tiene subordinados, inactivar directamente
                miembro.activo = False
                miembro.save()
                messages.success(request, f'{miembro.usuario.get_full_name() or miembro.usuario.username} inactivado exitosamente.')
                return redirect('sales:jerarquia_list')
            
            # Manejar reemplazo confirmado
            if request.POST.get('confirmar_reemplazo'):
                reemplazo_id = request.POST.get('reemplazo_id')
                if reemplazo_id:
                    try:
                        if rol == 'gerente':
                            reemplazo = GerenteEquipo.objects.get(id=reemplazo_id)
                            # Transferir todos los jefes de venta al reemplazo
                            subordinados = miembro.jefeventas.filter(activo=True)
                            for jefe in subordinados:
                                jefe.gerente_equipo = reemplazo
                                jefe.save()
                            # Activar el reemplazo
                            reemplazo.activo = True
                            reemplazo.save()
                        elif rol == 'jefe':
                            reemplazo = JefeVenta.objects.get(id=reemplazo_id)
                            # Transferir todos los team leaders al reemplazo
                            subordinados = miembro.teamleaders.filter(activo=True)
                            for tl in subordinados:
                                tl.jefe_venta = reemplazo
                                tl.save()
                            # Activar el reemplazo
                            reemplazo.activo = True
                            reemplazo.save()
                        elif rol == 'team_leader':
                            reemplazo = TeamLeader.objects.get(id=reemplazo_id)
                            # Transferir todos los vendedores al reemplazo
                            subordinados = miembro.vendedores.filter(activo=True)
                            for v in subordinados:
                                v.team_leader = reemplazo
                                v.save()
                            # Activar el reemplazo
                            reemplazo.activo = True
                            reemplazo.save()
                        
                        # Inactivar el miembro original
                        miembro.activo = False
                        miembro.save()
                        
                        messages.success(
                            request,
                            f'{miembro.usuario.get_full_name() or miembro.usuario.username} inactivado y '
                            f'{reemplazo.usuario.get_full_name() or reemplazo.usuario.username} activado como reemplazo.'
                        )
                        return redirect('sales:jerarquia_list')
                    except Exception as e:
                        messages.error(request, f'Error al realizar el reemplazo: {str(e)}')
                        return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
            
            # Verificar si se está activando un usuario inactivo
            if not miembro.activo and activo:
                # Si es gerente y se está activando, verificar conflictos
                if rol == 'gerente':
                    equipo_target = EquipoVenta.objects.get(id=nuevo_equipo_id)
                    gerente_activo_existente = GerenteEquipo.objects.filter(
                        equipo_venta=equipo_target, 
                        activo=True
                    ).exclude(id=miembro.id).first()
                    
                    if gerente_activo_existente:
                        # Verificar si el usuario ya confirmó el reemplazo
                        confirmar_reactivacion = request.POST.get('confirmar_reactivacion')
                        if not confirmar_reactivacion:
                            # Mostrar pantalla de confirmación similar a la de creación
                            context = {
                                'equipo': equipo_target,
                                'usuario_reactivar': miembro.usuario,
                                'gerente_actual': gerente_activo_existente,
                                'miembro_inactivo': miembro,
                                'rol': rol,
                                'requiere_confirmacion_reactivacion': True,
                                'title': 'Confirmar Reactivación de Gerente',
                            }
                            return render(request, 'sales/jerarquia/confirm_reactivate.html', context)
                        
                        # Usuario confirmó, transferir jefes de venta y desactivar gerente actual
                        jefes_de_venta = gerente_activo_existente.jefeventas.filter(activo=True)
                        
                        # Transferir todos los jefes de venta al gerente reactivado
                        jefes_transferidos = 0
                        for jefe in jefes_de_venta:
                            jefe.gerente_equipo = miembro
                            jefe.save()
                            jefes_transferidos += 1
                        
                        # Desactivar gerente actual
                        gerente_activo_existente.activo = False
                        gerente_activo_existente.save()
                        
                        messages.warning(
                            request, 
                            f'Gerente anterior ({gerente_activo_existente.usuario.get_full_name() or gerente_activo_existente.usuario.username}) desactivado.'
                        )
                        if jefes_transferidos > 0:
                            messages.info(request, f'{jefes_transferidos} jefe(s) de venta transferido(s) al gerente reactivado.')
            
            try:
                # Validaciones antes de cambiar de equipo
                if nuevo_equipo_id != str(equipo_actual.id):
                    # Verificar que no tenga subalternos
                    if rol == 'gerente' and miembro.jefeventas.filter(activo=True).exists():
                        messages.error(request, 'No se puede cambiar de equipo. El gerente tiene jefes de venta asignados.')
                        return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
                    elif rol == 'jefe' and miembro.teamleaders.filter(activo=True).exists():
                        messages.error(request, 'No se puede cambiar de equipo. El jefe tiene team leaders asignados.')
                        return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
                    elif rol == 'team_leader' and miembro.vendedores.filter(activo=True).exists():
                        messages.error(request, 'No se puede cambiar de equipo. El team leader tiene vendedores asignados.')
                        return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
                    elif rol == 'vendedor':
                        # TODO: Verificar que no tenga procesos de venta vigentes
                        # Por ahora permitimos el cambio
                        pass
                
                # Realizar los cambios
                nuevo_equipo = EquipoVenta.objects.get(id=nuevo_equipo_id)
                
                if rol == 'gerente':
                    # Validar desactivación de gerente
                    if miembro.activo and not activo:
                        # Se está intentando desactivar un gerente activo
                        # Verificar si es el único gerente activo del equipo
                        otros_gerentes_activos = GerenteEquipo.objects.filter(
                            equipo_venta=miembro.equipo_venta,
                            activo=True
                        ).exclude(id=miembro.id).exists()
                        
                        if not otros_gerentes_activos:
                            messages.error(
                                request,
                                f'No se puede desactivar a {miembro.usuario.get_full_name() or miembro.usuario.username}. '
                                f'Es el único gerente activo del equipo {miembro.equipo_venta.nombre}. '
                                f'Asigna otro gerente primero o usa "Cambiar Rol" para reemplazarlo.'
                            )
                            return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
                    
                    if nuevo_equipo_id != str(equipo_actual.id):
                        # Cambiar de equipo
                        nuevo_equipo = EquipoVenta.objects.get(id=nuevo_equipo_id)
                        
                        # Verificar si el nuevo equipo ya tiene un gerente activo
                        gerente_existente = GerenteEquipo.objects.filter(
                            equipo_venta=nuevo_equipo, 
                            activo=True
                        ).exclude(id=miembro.id).first()
                        
                        if gerente_existente:
                            messages.error(
                                request, 
                                f'El equipo {nuevo_equipo.nombre} ya tiene un gerente activo: '
                                f'{gerente_existente.usuario.get_full_name() or gerente_existente.usuario.username}'
                            )
                            return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
                        
                        miembro.equipo_venta = nuevo_equipo
                    
                    miembro.activo = activo
                    miembro.save()
                    
                elif rol in ['jefe', 'team_leader', 'vendedor']:
                    # Para otros roles, necesitamos cambiar el supervisor
                    if nuevo_supervisor_id:
                        if rol == 'jefe':
                            nuevo_supervisor = GerenteEquipo.objects.get(id=nuevo_supervisor_id)
                            miembro.gerente_equipo = nuevo_supervisor
                        elif rol == 'team_leader':
                            nuevo_supervisor = JefeVenta.objects.get(id=nuevo_supervisor_id)
                            miembro.jefe_venta = nuevo_supervisor
                        elif rol == 'vendedor':
                            nuevo_supervisor = TeamLeader.objects.get(id=nuevo_supervisor_id)
                            miembro.team_leader = nuevo_supervisor
                    
                    miembro.activo = activo
                    miembro.save()
                
                messages.success(request, f'Usuario actualizado exitosamente.')
                return redirect('sales:jerarquia_list')
                
            except Exception as e:
                messages.error(request, f'Error al actualizar: {str(e)}')
                return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
        
        # GET request - mostrar formulario
        equipos = EquipoVenta.objects.filter(activo=True).order_by('nombre')
        
        context = {
            'miembro': miembro,
            'rol': rol,
            'rol_display': rol.replace('_', ' ').title(),
            'equipo_actual': equipo_actual,
            'equipos': equipos,
            'title': f'Editar {rol.replace("_", " ").title()}',
        }
        
        return render(request, 'sales/jerarquia/edit.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar datos: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales.delete_equipoventa', raise_exception=True)
def jerarquia_member_delete(request, member_id, rol):
    """Eliminar un miembro de la jerarquía"""
    try:
        # Obtener el objeto según el rol
        if rol == 'gerente':
            miembro = get_object_or_404(GerenteEquipo, id=member_id)
            usuario = miembro.usuario
            equipo = miembro.equipo_venta
        elif rol == 'jefe':
            miembro = get_object_or_404(JefeVenta, id=member_id)
            usuario = miembro.usuario
            equipo = miembro.gerente_equipo.equipo_venta
        elif rol == 'team_leader':
            miembro = get_object_or_404(TeamLeader, id=member_id)
            usuario = miembro.usuario
            equipo = miembro.jefe_venta.gerente_equipo.equipo_venta
        elif rol == 'vendedor':
            miembro = get_object_or_404(Vendedor, id=member_id)
            usuario = miembro.usuario
            equipo = miembro.team_leader.jefe_venta.gerente_equipo.equipo_venta
        else:
            messages.error(request, 'Rol no válido.')
            return redirect('sales:jerarquia_list')
        
        if request.method == 'POST':
            try:
                # Validaciones antes de eliminar
                if rol == 'gerente' and miembro.jefeventas.filter(activo=True).exists():
                    messages.error(request, 'No se puede eliminar. El gerente tiene jefes de venta asignados.')
                    return redirect('sales:jerarquia_member_delete', member_id=member_id, rol=rol)
                elif rol == 'jefe' and miembro.teamleaders.filter(activo=True).exists():
                    messages.error(request, 'No se puede eliminar. El jefe tiene team leaders asignados.')
                    return redirect('sales:jerarquia_member_delete', member_id=member_id, rol=rol)
                elif rol == 'team_leader' and miembro.vendedores.filter(activo=True).exists():
                    messages.error(request, 'No se puede eliminar. El team leader tiene vendedores asignados.')
                    return redirect('sales:jerarquia_member_delete', member_id=member_id, rol=rol)
                elif rol == 'vendedor':
                    # TODO: Verificar que no tenga procesos de venta vigentes
                    # Por ahora permitimos la eliminación
                    pass
                
                # Eliminar el miembro
                usuario_nombre = usuario.get_full_name() or usuario.username
                miembro.delete()
                
                messages.success(request, f'{usuario_nombre} eliminado exitosamente del equipo {equipo.nombre}.')
                return redirect('sales:jerarquia_list')
                
            except Exception as e:
                messages.error(request, f'Error al eliminar: {str(e)}')
                return redirect('sales:jerarquia_member_delete', member_id=member_id, rol=rol)
        
        # GET request - mostrar confirmación
        # Verificar si puede eliminar
        puede_eliminar = True
        razon_bloqueo = []
        
        if rol == 'gerente' and miembro.jefeventas.filter(activo=True).exists():
            puede_eliminar = False
            razon_bloqueo.append(f"{miembro.jefeventas.filter(activo=True).count()} jefes de venta asignados")
        elif rol == 'jefe' and miembro.teamleaders.filter(activo=True).exists():
            puede_eliminar = False
            razon_bloqueo.append(f"{miembro.teamleaders.filter(activo=True).count()} team leaders asignados")
        elif rol == 'team_leader' and miembro.vendedores.filter(activo=True).exists():
            puede_eliminar = False
            razon_bloqueo.append(f"{miembro.vendedores.filter(activo=True).count()} vendedores asignados")
        
        context = {
            'miembro': miembro,
            'usuario': usuario,
            'equipo': equipo,
            'rol': rol,
            'rol_display': rol.replace('_', ' ').title(),
            'puede_eliminar': puede_eliminar,
            'razon_bloqueo': razon_bloqueo,
            'title': f'Eliminar {rol.replace("_", " ").title()}',
        }
        
        return render(request, 'sales/jerarquia/delete.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar datos: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
def jerarquia_member_reassign(request, member_id, rol):
    """Reasignar un miembro a un nuevo rol (degradar/promover)"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Obtener el miembro actual
        if rol == 'gerente':
            miembro_actual = get_object_or_404(GerenteEquipo, id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.equipo_venta
        elif rol == 'jefe':
            miembro_actual = get_object_or_404(JefeVenta, id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.gerente_equipo.equipo_venta
        elif rol == 'team_leader':
            miembro_actual = get_object_or_404(TeamLeader, id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.jefe_venta.gerente_equipo.equipo_venta
        elif rol == 'vendedor':
            miembro_actual = get_object_or_404(Vendedor, id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.team_leader.jefe_venta.gerente_equipo.equipo_venta
        else:
            messages.error(request, 'Rol no válido.')
            return redirect('sales:jerarquia_list')
        
        if request.method == 'POST':
            nuevo_rol = request.POST.get('nuevo_rol')
            nuevo_equipo_id = request.POST.get('equipo')
            supervisor_id = request.POST.get('supervisor')
            confirmar_reemplazo = request.POST.get('confirmar_reemplazo')
            
            # Verificar que solo usuarios inactivos pueden ser promovidos/degradados
            if miembro_actual.activo:
                messages.error(
                    request,
                    f'Solo usuarios inactivos pueden ser promovidos o degradados. '
                    f'Primero inactiva a {usuario.get_full_name() or usuario.username} antes de cambiar su rol.'
                )
                return redirect('sales:jerarquia_member_reassign', member_id=member_id, rol=rol)
            
            try:
                nuevo_equipo = EquipoVenta.objects.get(id=nuevo_equipo_id)
                
                # Determinar tipo de cambio
                orden_roles = {'vendedor': 1, 'team_leader': 2, 'jefe': 3, 'gerente': 4}
                rol_actual_nivel = orden_roles.get(rol, 0)
                nuevo_rol_nivel = orden_roles.get(nuevo_rol, 0)
                
                if nuevo_rol_nivel > rol_actual_nivel:
                    tipo_cambio = "promocion"
                elif nuevo_rol_nivel < rol_actual_nivel:
                    tipo_cambio = "degradacion"
                else:
                    tipo_cambio = "lateral"
                
                # Validaciones según el nuevo rol
                if nuevo_rol == 'gerente':
                    # Verificar si hay gerente activo en el equipo destino
                    gerente_existente = GerenteEquipo.objects.filter(
                        equipo_venta=nuevo_equipo, 
                        activo=True
                    ).first()
                    
                    if gerente_existente and not confirmar_reemplazo:
                        # Mostrar pantalla de confirmación para reemplazo
                        context = {
                            'miembro': miembro_actual,
                            'usuario': usuario,
                            'rol_actual': rol,
                            'rol_display_actual': rol.replace('_', ' ').title(),
                            'equipo_actual': equipo_actual,
                            'equipo_destino': nuevo_equipo,
                            'gerente_actual': gerente_existente,
                            'tipo_cambio': tipo_cambio,
                            'tipo_reemplazo': 'gerente',
                            'title': 'Confirmar Reasignación como Gerente',
                        }
                        return render(request, 'sales/jerarquia/confirm_reassign.html', context)
                    
                    elif gerente_existente and confirmar_reemplazo:
                        # Usuario confirmó, transferir jefes de venta y desactivar gerente actual
                        jefes_de_venta = gerente_existente.jefeventas.filter(activo=True)
                        
                        # Crear el nuevo gerente primero
                        nuevo_gerente = GerenteEquipo.objects.create(usuario=usuario, equipo_venta=nuevo_equipo)
                        
                        # Transferir todos los jefes de venta al nuevo gerente
                        jefes_transferidos = 0
                        for jefe in jefes_de_venta:
                            jefe.gerente_equipo = nuevo_gerente
                            jefe.save()
                            jefes_transferidos += 1
                        
                        # Desactivar el gerente anterior
                        gerente_existente.activo = False
                        gerente_existente.save()
                        
                        # Eliminar asignación actual del usuario
                        miembro_actual.delete()
                        
                        messages.success(
                            request,
                            f'{usuario.get_full_name() or usuario.username} promovido exitosamente a Gerente '
                            f'en {nuevo_equipo.nombre}. Se desactivó el gerente anterior y se transfirieron '
                            f'{jefes_transferidos} jefes de venta.'
                        )
                        return redirect('sales:jerarquia_list')
                
                elif nuevo_rol == 'jefe':
                    # Para jefes de venta, pueden coexistir múltiples bajo un gerente
                    # No hay conflictos por defecto - simplemente asignamos
                    pass
                
                elif nuevo_rol == 'team_leader':
                    # Para team leaders, pueden coexistir múltiples bajo un jefe de venta
                    # No hay conflictos por defecto - simplemente asignamos
                    pass
                
                # Eliminar asignación actual
                miembro_actual.delete()
                
                # Crear nueva asignación
                if nuevo_rol == 'gerente':
                    GerenteEquipo.objects.create(usuario=usuario, equipo_venta=nuevo_equipo)
                elif nuevo_rol == 'jefe':
                    supervisor = GerenteEquipo.objects.get(id=supervisor_id)
                    JefeVenta.objects.create(usuario=usuario, gerente_equipo=supervisor)
                elif nuevo_rol == 'team_leader':
                    supervisor = JefeVenta.objects.get(id=supervisor_id)
                    TeamLeader.objects.create(usuario=usuario, jefe_venta=supervisor)
                elif nuevo_rol == 'vendedor':
                    supervisor = TeamLeader.objects.get(id=supervisor_id)
                    Vendedor.objects.create(usuario=usuario, team_leader=supervisor)
                
                # Determinar si fue promoción o degradación
                orden_roles = {'vendedor': 1, 'team_leader': 2, 'jefe': 3, 'gerente': 4}
                rol_actual_nivel = orden_roles.get(rol, 0)
                nuevo_rol_nivel = orden_roles.get(nuevo_rol, 0)
                
                if nuevo_rol_nivel > rol_actual_nivel:
                    accion = "promovido"
                elif nuevo_rol_nivel < rol_actual_nivel:
                    accion = "degradado"
                else:
                    accion = "reasignado"
                
                messages.success(
                    request, 
                    f'{usuario.get_full_name() or usuario.username} {accion} exitosamente de '
                    f'{rol.replace("_", " ").title()} a {nuevo_rol.replace("_", " ").title()} '
                    f'en {nuevo_equipo.nombre}.'
                )
                return redirect('sales:jerarquia_list')
                
            except Exception as e:
                messages.error(request, f'Error al reasignar: {str(e)}')
                return redirect('sales:jerarquia_member_reassign', member_id=member_id, rol=rol)
        
        # GET request - mostrar formulario
        equipos = EquipoVenta.objects.filter(activo=True).order_by('nombre')
        
        # Roles disponibles para degradación/promoción
        roles_disponibles = [
            ('gerente', 'Gerente de Equipo'),
            ('jefe', 'Jefe de Venta'),
            ('team_leader', 'Team Leader'),
            ('vendedor', 'Vendedor'),
        ]
        
        context = {
            'miembro': miembro_actual,
            'usuario': usuario,
            'rol_actual': rol,
            'rol_display': rol.replace('_', ' ').title(),
            'equipo_actual': equipo_actual,
            'equipos': equipos,
            'roles_disponibles': roles_disponibles,
            'title': f'Reasignar {rol.replace("_", " ").title()}',
        }
        
        return render(request, 'sales/jerarquia/reassign.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar datos: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales.change_gerenteequipo', raise_exception=True)
def jerarquia_member_deactivate(request, member_id, rol):
    """
    Vista para inactivar un miembro de jerarquía con diálogo de reemplazo
    """
    try:
        # Obtener el miembro actual
        miembro_actual, usuario, equipo_actual = get_member_by_role(member_id, rol)
        
        if not miembro_actual:
            messages.error(request, 'Miembro no encontrado.')
            return redirect('sales:jerarquia_list')
        
        # Si es vendedor, permitir inactivación directa
        if rol == 'vendedor':
            return redirect('sales:jerarquia_member_toggle_status', member_id=member_id, rol=rol)
        
        # Para otros roles, verificar si tiene subordinados
        has_subordinados = False
        subordinados_info = []
        
        if rol == 'gerente':
            subordinados = JefeVenta.objects.filter(gerente_equipo=miembro_actual, activo=True)
            has_subordinados = subordinados.exists()
            for subordinado in subordinados:
                subordinados_info.append({
                    'nombre': subordinado.usuario.get_full_name() or subordinado.usuario.username,
                    'rol': 'Jefe de Venta'
                })
        elif rol == 'jefe':
            subordinados = TeamLeader.objects.filter(jefe_venta=miembro_actual, activo=True)
            has_subordinados = subordinados.exists()
            for subordinado in subordinados:
                subordinados_info.append({
                    'nombre': subordinado.usuario.get_full_name() or subordinado.usuario.username,
                    'rol': 'Team Leader'
                })
        elif rol == 'team_leader':
            subordinados = Vendedor.objects.filter(team_leader=miembro_actual, activo=True)
            has_subordinados = subordinados.exists()
            for subordinado in subordinados:
                subordinados_info.append({
                    'nombre': subordinado.usuario.get_full_name() or subordinado.usuario.username,
                    'rol': 'Vendedor'
                })
        
        if request.method == 'POST':
            confirmar = request.POST.get('confirmar')
            if not confirmar:
                messages.error(request, 'Debes confirmar la inactivación.')
                return redirect('sales:jerarquia_member_deactivate', member_id=member_id, rol=rol)
                
            if has_subordinados:
                reemplazo_id = request.POST.get('reemplazo')
                if not reemplazo_id:
                    messages.error(request, 'Debes seleccionar un reemplazo para este usuario.')
                    return redirect('sales:jerarquia_member_deactivate', member_id=member_id, rol=rol)
                
                # Transferir subordinados al reemplazo
                try:
                    from django.contrib.auth.models import User
                    if reemplazo_id.startswith('user_'):
                        # Es un usuario sin equipo
                        user_id = reemplazo_id.replace('user_', '')
                        reemplazo_usuario = User.objects.get(id=user_id)
                        
                        if rol == 'gerente':
                            # Crear nuevo gerente y transferir jefes
                            nuevo_gerente = GerenteEquipo.objects.create(
                                usuario=reemplazo_usuario, 
                                equipo_venta=equipo_actual
                            )
                            subordinados = JefeVenta.objects.filter(gerente_equipo=miembro_actual, activo=True)
                            for subordinado in subordinados:
                                subordinado.gerente_equipo = nuevo_gerente
                                subordinado.save()
                                
                    else:
                        # Es un miembro existente inactivo - reactivarlo
                        if rol == 'gerente':
                            reemplazo_gerente = GerenteEquipo.objects.get(id=reemplazo_id)
                            reemplazo_gerente.activo = True
                            reemplazo_gerente.save()
                            
                            # Transferir subordinados
                            subordinados = JefeVenta.objects.filter(gerente_equipo=miembro_actual, activo=True)
                            for subordinado in subordinados:
                                subordinado.gerente_equipo = reemplazo_gerente
                                subordinado.save()
                                
                    messages.success(
                        request,
                        f'Subordinados transferidos exitosamente al reemplazo.'
                    )
                    
                except Exception as e:
                    messages.error(request, f'Error al transferir subordinados: {str(e)}')
                    return redirect('sales:jerarquia_member_deactivate', member_id=member_id, rol=rol)
            
            # Inactivar el miembro
            miembro_actual.activo = False
            miembro_actual.save()
            
            mensaje_exito = f'{usuario.get_full_name() or usuario.username} ha sido inactivado exitosamente.'
            if has_subordinados:
                mensaje_exito += f' Sus subordinados han sido transferidos al reemplazo seleccionado.'
            
            messages.success(request, mensaje_exito)
            return redirect('sales:jerarquia_list')
        
        # GET - mostrar diálogo de confirmación
        replacements = []
        if has_subordinados:
            # Buscar usuarios disponibles para reemplazo
            from django.contrib.auth.models import User
            from django.db.models import Q
            
            # Usuarios inactivos del mismo equipo
            equipos_ids = [equipo_actual.id]
            users_in_same_team = []
            
            if rol == 'gerente':
                # Buscar gerentes inactivos del mismo equipo
                gerentes_inactivos = GerenteEquipo.objects.filter(
                    equipo_venta=equipo_actual, activo=False
                ).select_related('usuario')
                for gerente in gerentes_inactivos:
                    users_in_same_team.append({
                        'id': gerente.id,
                        'nombre': gerente.usuario.get_full_name() or gerente.usuario.username,
                        'email': gerente.usuario.email,
                        'tipo': 'Gerente Inactivo - Mismo Equipo'
                    })
            
            # Usuarios inactivos de otros equipos
            # Usuarios sin equipo asignado
            usuarios_sin_equipo = User.objects.exclude(
                Q(gerenteequipo__activo=True) | 
                Q(jefeventa__activo=True) | 
                Q(teamleader__activo=True) | 
                Q(vendedor__activo=True)
            ).filter(is_active=True)
            
            for usuario_libre in usuarios_sin_equipo:
                replacements.append({
                    'id': f'user_{usuario_libre.id}',
                    'nombre': usuario_libre.get_full_name() or usuario_libre.username,
                    'email': usuario_libre.email,
                    'tipo': 'Usuario Sin Equipo'
                })
            
            replacements.extend(users_in_same_team)
        
        context = {
            'miembro': miembro_actual,
            'usuario': usuario,
            'rol': rol,
            'rol_display': rol.replace('_', ' ').title(),
            'equipo_actual': equipo_actual,
            'has_subordinados': has_subordinados,
            'subordinados_info': subordinados_info,
            'replacements': replacements,
            'title': f'Inactivar {rol.replace("_", " ").title()}',
        }
        
        return render(request, 'sales/jerarquia/deactivate.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al procesar solicitud: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales.change_gerenteequipo', raise_exception=True)
def jerarquia_member_toggle_status(request, member_id, rol):
    """
    Vista para alternar el estado activo/inactivo de un miembro
    """
    try:
        # Obtener el miembro actual
        miembro_actual, usuario, equipo_actual = get_member_by_role(member_id, rol)
        
        if not miembro_actual:
            messages.error(request, 'Miembro no encontrado.')
            return redirect('sales:jerarquia_list')
        
        # Si está activo y queremos inactivarlo, verificar subordinados
        if miembro_actual.activo and rol != 'vendedor':
            # Verificar si tiene subordinados
            has_subordinados = False
            
            if rol == 'gerente':
                has_subordinados = JefeVenta.objects.filter(gerente_equipo=miembro_actual, activo=True).exists()
            elif rol == 'jefe':
                has_subordinados = TeamLeader.objects.filter(jefe_venta=miembro_actual, activo=True).exists()
            elif rol == 'team_leader':
                has_subordinados = Vendedor.objects.filter(team_leader=miembro_actual, activo=True).exists()
            
            if has_subordinados:
                # Redirigir al diálogo de inactivación con reemplazo
                messages.warning(
                    request,
                    f'{usuario.get_full_name() or usuario.username} tiene subordinados asignados. '
                    f'Debes seleccionar un reemplazo antes de inactivarlo.'
                )
                return redirect('sales:jerarquia_member_deactivate', member_id=member_id, rol=rol)
        
        # Alternar estado (solo si no tiene subordinados o es activación)
        miembro_actual.activo = not miembro_actual.activo
        miembro_actual.save()
        
        if miembro_actual.activo:
            messages.success(
                request,
                f'{usuario.get_full_name() or usuario.username} ha sido activado exitosamente.'
            )
        else:
            messages.success(
                request,
                f'{usuario.get_full_name() or usuario.username} ha sido inactivado exitosamente.'
            )
        
        return redirect('sales:jerarquia_list')
        
    except Exception as e:
        messages.error(request, f'Error al cambiar estado: {str(e)}')
        return redirect('sales:jerarquia_list')


# ============================================================
# VISTAS PARA PROYECTOS
# ============================================================

@login_required
@permission_required('sales.view_proyecto', raise_exception=True)
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
    return render(request, 'sales/proyectos/list.html', context)


@login_required
@permission_required('sales.view_proyecto', raise_exception=True)
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
            precio_min=models.Min('precio_venta'),
            precio_max=models.Max('precio_venta'),
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
    return render(request, 'sales/proyectos/detail.html', context)


@login_required
@permission_required('sales.add_proyecto', raise_exception=True)
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
    return render(request, 'sales/proyectos/form.html', context)


@login_required
@permission_required('sales.change_proyecto', raise_exception=True)
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
    return render(request, 'sales/proyectos/form.html', context)


@login_required
@permission_required('sales.delete_proyecto', raise_exception=True)
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
    return render(request, 'sales/proyectos/delete.html', context)


# ============================================================
# VISTAS PARA INMUEBLES
# ============================================================

@login_required
@permission_required('sales.view_inmueble', raise_exception=True)
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
    return render(request, 'sales/inmuebles/list.html', context)


@login_required
@permission_required('sales.view_inmueble', raise_exception=True)
def inmuebles_detail(request, proyecto_pk, pk):
    """Ver detalles de un inmueble"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)
    inmueble = get_object_or_404(Inmueble, pk=pk, proyecto=proyecto)

    context = {
        'proyecto': proyecto,
        'inmueble': inmueble,
        'title': f'Inmueble: {inmueble.codigo}',
    }
    return render(request, 'sales/inmuebles/detail.html', context)


@login_required
@permission_required('sales.add_inmueble', raise_exception=True)
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
    return render(request, 'sales/inmuebles/form.html', context)


@login_required
@permission_required('sales.change_inmueble', raise_exception=True)
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
    return render(request, 'sales/inmuebles/form.html', context)


@login_required
@permission_required('sales.delete_inmueble', raise_exception=True)
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
    return render(request, 'sales/inmuebles/delete.html', context)


# ============================================================
# VISTAS PARA COMISIONES
# ============================================================

@login_required
@permission_required('sales.change_proyecto', raise_exception=True)
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
    return render(request, 'sales/comisiones/desarrollo_form.html', context)


@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
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
    return render(request, 'sales/comisiones/venta_form.html', context)


# ============================================================
# VISTAS PARA GESTIÓN DE EQUIPOS (JERARQUÍA)
# ============================================================

@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
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
    return render(request, 'sales/equipos/hierarchy.html', context)


@login_required
@permission_required('sales.add_gerenteequipo', raise_exception=True)
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
    return render(request, 'sales/equipos/add_gerente.html', context)


@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
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
    
    import json
    
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
    return render(request, 'sales/equipos/add_member.html', context)


def equipos_list_members(request, pk):
    """Vista simple de lista de miembros para gestión diaria"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)
    
    # Construir lista plana de todos los miembros
    members = []
    
    # Gerentes
    for gerente in equipo.gerenteequipo_set.select_related('usuario').all():
        members.append({
            'id': gerente.id,
            'usuario': gerente.usuario,
            'role_type': 'gerente',
            'role_display': 'Gerente de Equipo',
            'role_color': 'bg-blue-500',
            'role_icon': 'fas fa-user-tie',
            'role_badge_color': 'bg-blue-100 text-blue-800',
            'supervisor': None,
            'supervisor_color': '',
            'supervisor_icon': '',
            'activo': gerente.activo,
        })
    
    # Jefes de Venta
    for gerente in equipo.gerenteequipo_set.all():
        for jefe in gerente.jefeventas.select_related('usuario').all():
            members.append({
                'id': jefe.id,
                'usuario': jefe.usuario,
                'role_type': 'jefe_venta',
                'role_display': 'Jefe de Venta',
                'role_color': 'bg-green-500',
                'role_icon': 'fas fa-user-cog',
                'role_badge_color': 'bg-green-100 text-green-800',
                'supervisor': gerente,
                'supervisor_color': 'bg-blue-500',
                'supervisor_icon': 'fas fa-user-tie',
                'activo': jefe.activo,
            })
    
    # Team Leaders
    for gerente in equipo.gerenteequipo_set.all():
        for jefe in gerente.jefeventas.all():
            for leader in jefe.teamleaders.select_related('usuario').all():
                members.append({
                    'id': leader.id,
                    'usuario': leader.usuario,
                    'role_type': 'team_leader',
                    'role_display': 'Team Leader',
                    'role_color': 'bg-purple-500',
                    'role_icon': 'fas fa-users',
                    'role_badge_color': 'bg-purple-100 text-purple-800',
                    'supervisor': jefe,
                    'supervisor_color': 'bg-green-500',
                    'supervisor_icon': 'fas fa-user-cog',
                    'activo': leader.activo,
                })
    
    # Vendedores
    for gerente in equipo.gerenteequipo_set.all():
        for jefe in gerente.jefeventas.all():
            for leader in jefe.teamleaders.all():
                for vendedor in leader.vendedores.select_related('usuario').all():
                    members.append({
                        'id': vendedor.id,
                        'usuario': vendedor.usuario,
                        'role_type': 'vendedor',
                        'role_display': 'Vendedor',
                        'role_color': 'bg-orange-500',
                        'role_icon': 'fas fa-user',
                        'role_badge_color': 'bg-orange-100 text-orange-800',
                        'supervisor': leader,
                        'supervisor_color': 'bg-purple-500',
                        'supervisor_icon': 'fas fa-users',
                        'activo': vendedor.activo,
                    })
    
    # Estadísticas
    stats = {
        'total_gerentes': sum(1 for m in members if m['role_type'] == 'gerente' and m['activo']),
        'total_jefes': sum(1 for m in members if m['role_type'] == 'jefe_venta' and m['activo']),
        'total_leaders': sum(1 for m in members if m['role_type'] == 'team_leader' and m['activo']),
        'total_vendedores': sum(1 for m in members if m['role_type'] == 'vendedor' and m['activo']),
    }
    
    # Ordenar por rol y luego por nombre
    role_order = {'gerente': 1, 'jefe_venta': 2, 'team_leader': 3, 'vendedor': 4}
    members.sort(key=lambda x: (
        role_order.get(x['role_type'], 5),
        x['usuario'].get_full_name() or x['usuario'].username
    ))
    
    # Obtener equipos disponibles para migración
    equipos_disponibles = EquipoVenta.objects.filter(activo=True).exclude(id=equipo.id).order_by('nombre')
    
    context = {
        'equipo': equipo,
        'members': members,
        'stats': stats,
        'total_members': len(members),
        'equipos_disponibles': equipos_disponibles,
        'title': f'Miembros - {equipo.nombre}',
    }
    return render(request, 'sales/equipos/list_members.html', context)


def equipos_list_members_test(request, pk):
    """Vista simple de lista de miembros SIN restricciones para testing"""
    equipo = get_object_or_404(EquipoVenta, pk=pk)
    
    # Construir lista plana de todos los miembros
    members = []
    
    # Gerentes
    for gerente in equipo.gerenteequipo_set.select_related('usuario').all():
        members.append({
            'id': gerente.id,
            'usuario': gerente.usuario,
            'role_type': 'gerente',
            'role_display': 'Gerente de Equipo',
            'role_color': 'bg-blue-500',
            'role_icon': 'fas fa-user-tie',
            'role_badge_color': 'bg-blue-100 text-blue-800',
            'supervisor': None,
            'supervisor_color': '',
            'supervisor_icon': '',
            'activo': gerente.activo,
        })
    
    # Jefes de Venta
    for gerente in equipo.gerenteequipo_set.all():
        for jefe in gerente.jefeventas.select_related('usuario').all():
            members.append({
                'id': jefe.id,
                'usuario': jefe.usuario,
                'role_type': 'jefe_venta',
                'role_display': 'Jefe de Venta',
                'role_color': 'bg-green-500',
                'role_icon': 'fas fa-user-cog',
                'role_badge_color': 'bg-green-100 text-green-800',
                'supervisor': gerente,
                'supervisor_color': 'bg-blue-500',
                'supervisor_icon': 'fas fa-user-tie',
                'activo': jefe.activo,
            })
    
    # Team Leaders
    for gerente in equipo.gerenteequipo_set.all():
        for jefe in gerente.jefeventas.all():
            for leader in jefe.teamleaders.select_related('usuario').all():
                members.append({
                    'id': leader.id,
                    'usuario': leader.usuario,
                    'role_type': 'team_leader',
                    'role_display': 'Team Leader',
                    'role_color': 'bg-purple-500',
                    'role_icon': 'fas fa-users',
                    'role_badge_color': 'bg-purple-100 text-purple-800',
                    'supervisor': jefe,
                    'supervisor_color': 'bg-green-500',
                    'supervisor_icon': 'fas fa-user-cog',
                    'activo': leader.activo,
                })
    
    # Vendedores
    for gerente in equipo.gerenteequipo_set.all():
        for jefe in gerente.jefeventas.all():
            for leader in jefe.teamleaders.all():
                for vendedor in leader.vendedores.select_related('usuario').all():
                    members.append({
                        'id': vendedor.id,
                        'usuario': vendedor.usuario,
                        'role_type': 'vendedor',
                        'role_display': 'Vendedor',
                        'role_color': 'bg-orange-500',
                        'role_icon': 'fas fa-user',
                        'role_badge_color': 'bg-orange-100 text-orange-800',
                        'supervisor': leader,
                        'supervisor_color': 'bg-purple-500',
                        'supervisor_icon': 'fas fa-users',
                        'activo': vendedor.activo,
                    })
    
    # Estadísticas
    stats = {
        'total_gerentes': sum(1 for m in members if m['role_type'] == 'gerente' and m['activo']),
        'total_jefes': sum(1 for m in members if m['role_type'] == 'jefe_venta' and m['activo']),
        'total_leaders': sum(1 for m in members if m['role_type'] == 'team_leader' and m['activo']),
        'total_vendedores': sum(1 for m in members if m['role_type'] == 'vendedor' and m['activo']),
    }
    
    # Ordenar por rol y luego por nombre
    role_order = {'gerente': 1, 'jefe_venta': 2, 'team_leader': 3, 'vendedor': 4}
    members.sort(key=lambda x: (
        role_order.get(x['role_type'], 5),
        x['usuario'].get_full_name() or x['usuario'].username
    ))
    
    # Obtener equipos disponibles para migración
    equipos_disponibles = EquipoVenta.objects.filter(activo=True).exclude(id=equipo.id).order_by('nombre')
    
    context = {
        'equipo': equipo,
        'members': members,
        'stats': stats,
        'total_members': len(members),
        'equipos_disponibles': equipos_disponibles,
        'title': f'Miembros TEST - {equipo.nombre}',
    }
    return render(request, 'sales/equipos/list_members.html', context)


# ============================================================
# VISTAS AJAX Y API
# ============================================================

@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
def ajax_cambiar_estado_miembro(request):
    """Cambiar estado activo/inactivo de un miembro del equipo via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        tipo_miembro = request.POST.get('tipo')
        miembro_id = request.POST.get('miembro_id')
        nuevo_estado = request.POST.get('activo') == 'true'
        
        if not all([tipo_miembro, miembro_id]):
            return JsonResponse({'success': False, 'error': 'Parámetros faltantes'})
        
        # Buscar el miembro según su tipo
        if tipo_miembro == 'gerente':
            miembro = get_object_or_404(GerenteEquipo, id=miembro_id)
        elif tipo_miembro == 'jefe_venta':
            miembro = get_object_or_404(JefeVenta, id=miembro_id)
        elif tipo_miembro == 'team_leader':
            miembro = get_object_or_404(TeamLeader, id=miembro_id)
        elif tipo_miembro == 'vendedor':
            miembro = get_object_or_404(Vendedor, id=miembro_id)
        else:
            return JsonResponse({'success': False, 'error': 'Tipo de miembro inválido'})
        
        # Validación especial para gerentes
        if tipo_miembro == 'gerente' and nuevo_estado:
            # Si se está activando un gerente, verificar que no haya otro activo
            equipo = miembro.equipo_venta
            otros_gerentes_activos = equipo.gerenteequipo_set.filter(activo=True).exclude(id=miembro_id)
            if otros_gerentes_activos.exists():
                return JsonResponse({
                    'success': False, 
                    'error': 'Solo puede haber un gerente activo por equipo. Desactiva el gerente actual primero.'
                })
        
        # Cambiar el estado
        miembro.activo = nuevo_estado
        miembro.save()
        
        accion = 'activado' if nuevo_estado else 'desactivado'
        nombre_usuario = miembro.usuario.get_full_name() or miembro.usuario.username
        
        return JsonResponse({
            'success': True, 
            'message': f'{nombre_usuario} ha sido {accion} exitosamente.',
            'nuevo_estado': nuevo_estado
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('sales.change_equipoventa', raise_exception=True)
def ajax_migrar_miembro(request):
    """Migrar un miembro a otro equipo via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        tipo_miembro = request.POST.get('tipo')
        miembro_id = request.POST.get('miembro_id')
        nuevo_equipo_id = request.POST.get('nuevo_equipo_id')
        
        if not all([tipo_miembro, miembro_id, nuevo_equipo_id]):
            return JsonResponse({'success': False, 'error': 'Parámetros faltantes'})
        
        # Buscar el miembro y el nuevo equipo
        nuevo_equipo = get_object_or_404(EquipoVenta, id=nuevo_equipo_id, activo=True)
        
        if tipo_miembro == 'gerente':
            miembro = get_object_or_404(GerenteEquipo, id=miembro_id)
            
            # Verificar que el nuevo equipo no tenga gerente activo
            if nuevo_equipo.gerenteequipo_set.filter(activo=True).exists():
                return JsonResponse({
                    'success': False, 
                    'error': f'El equipo "{nuevo_equipo.nombre}" ya tiene un gerente activo.'
                })
            
            # Migrar
            miembro.equipo_venta = nuevo_equipo
            miembro.save()
            
        elif tipo_miembro == 'jefe_venta':
            miembro = get_object_or_404(JefeVenta, id=miembro_id)
            
            # Buscar un gerente activo en el nuevo equipo
            gerente_nuevo_equipo = nuevo_equipo.gerenteequipo_set.filter(activo=True).first()
            if not gerente_nuevo_equipo:
                return JsonResponse({
                    'success': False, 
                    'error': f'El equipo "{nuevo_equipo.nombre}" no tiene un gerente activo.'
                })
            
            # Migrar
            miembro.gerente_equipo = gerente_nuevo_equipo
            miembro.save()
            
        elif tipo_miembro == 'team_leader':
            miembro = get_object_or_404(TeamLeader, id=miembro_id)
            
            # Buscar un jefe de venta activo en el nuevo equipo
            jefe_nuevo_equipo = None
            for gerente in nuevo_equipo.gerenteequipo_set.filter(activo=True):
                jefe_nuevo_equipo = gerente.jefeventas.filter(activo=True).first()
                if jefe_nuevo_equipo:
                    break
            
            if not jefe_nuevo_equipo:
                return JsonResponse({
                    'success': False, 
                    'error': f'El equipo "{nuevo_equipo.nombre}" no tiene jefes de venta activos.'
                })
            
            # Migrar
            miembro.jefe_venta = jefe_nuevo_equipo
            miembro.save()
            
        elif tipo_miembro == 'vendedor':
            miembro = get_object_or_404(Vendedor, id=miembro_id)
            
            # Buscar un team leader activo en el nuevo equipo
            team_leader_nuevo_equipo = None
            for gerente in nuevo_equipo.gerenteequipo_set.filter(activo=True):
                for jefe in gerente.jefeventas.filter(activo=True):
                    team_leader_nuevo_equipo = jefe.teamleaders.filter(activo=True).first()
                    if team_leader_nuevo_equipo:
                        break
                if team_leader_nuevo_equipo:
                    break
            
            if not team_leader_nuevo_equipo:
                return JsonResponse({
                    'success': False, 
                    'error': f'El equipo "{nuevo_equipo.nombre}" no tiene team leaders activos.'
                })
            
            # Migrar
            miembro.team_leader = team_leader_nuevo_equipo
            miembro.save()
            
        else:
            return JsonResponse({'success': False, 'error': 'Tipo de miembro inválido'})
        
        nombre_usuario = miembro.usuario.get_full_name() or miembro.usuario.username
        return JsonResponse({
            'success': True, 
            'message': f'{nombre_usuario} ha sido migrado al equipo "{nuevo_equipo.nombre}" exitosamente.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def ajax_equipos_search(request):
    """Búsqueda AJAX de equipos para autocompletado"""
    query = request.GET.get('q', '')
    equipos = EquipoVenta.objects.filter(
        nombre__icontains=query,
        activo=True
    ).values('id', 'nombre')[:10]

    return JsonResponse({
        'results': list(equipos)
    })


@login_required
def ajax_proyectos_search(request):
    """Búsqueda AJAX de proyectos para autocompletado"""
    query = request.GET.get('q', '')
    proyectos = Proyecto.objects.filter(
        nombre__icontains=query,
        activo=True
    ).values('id', 'nombre', 'estado')[:10]

    return JsonResponse({
        'results': list(proyectos)
    })


@login_required
def ajax_inmuebles_by_proyecto(request, proyecto_pk):
    """Obtener inmuebles de un proyecto via AJAX"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk)
    inmuebles = proyecto.inmuebles.filter(
        disponible=True,
        estado='disponible'
    ).values('id', 'codigo', 'tipo', 'precio_venta')

    return JsonResponse({
        'results': list(inmuebles)
    })


# ============================================================
# DASHBOARD Y ESTADÍSTICAS
# ============================================================

@login_required
@permission_required('sales.view_proyecto', raise_exception=True)
def sales_dashboard(request):
    """Dashboard principal de ventas"""
    # Estadísticas generales
    stats = {
        'total_proyectos': Proyecto.objects.filter(activo=True).count(),
        'total_equipos': EquipoVenta.objects.filter(activo=True).count(),
        'total_inmuebles': Inmueble.objects.count(),
        'inmuebles_disponibles': Inmueble.objects.filter(
            disponible=True,
            estado='disponible'
        ).count(),
        'inmuebles_vendidos': Inmueble.objects.filter(estado='vendido').count(),
    }

    # Proyectos más activos (con más inmuebles)
    proyectos_activos = Proyecto.objects.filter(
        activo=True
    ).annotate(
        total_inmuebles=Count('inmuebles'),
        inmuebles_vendidos=Count('inmuebles', filter=Q(inmuebles__estado='vendido'))
    ).order_by('-total_inmuebles')[:5]

    # Equipos con más vendedores
    equipos_grandes = EquipoVenta.objects.filter(
        activo=True
    ).annotate(
        total_gerentes=Count('gerenteequipo', filter=Q(gerenteequipo__activo=True))
    ).order_by('-total_gerentes')[:5]

    context = {
        'stats': stats,
        'proyectos_activos': proyectos_activos,
        'equipos_grandes': equipos_grandes,
        'title': 'Dashboard de Ventas',
    }
    return render(request, 'sales/dashboard.html', context)


# ============================================================
# VISTAS AJAX
# ============================================================

@login_required
def ajax_get_supervisores(request):
    """Obtener supervisores disponibles según equipo y rol"""
    equipo_id = request.GET.get('equipo')
    rol = request.GET.get('rol')
    usuario_actual_id = request.GET.get('usuario_actual')  # Usuario que se está editando/promoviendo
    
    supervisores = []
    advertencia = None
    
    try:
        equipo = EquipoVenta.objects.get(id=equipo_id)
        
        # Verificar si hay gerente activo para roles que lo requieren como jefe directo
        if rol == 'jefe':
            gerente_activo = GerenteEquipo.objects.filter(equipo_venta=equipo, activo=True).first()
            if not gerente_activo:
                advertencia = "Este equipo no tiene un gerente activo. Primero debes asignar un gerente."
                return JsonResponse({'supervisores': supervisores, 'advertencia': advertencia})
        
        if rol == 'jefe':
            # Para jefes de venta, los jefes directos son los gerentes del equipo
            gerentes = GerenteEquipo.objects.filter(equipo_venta=equipo, activo=True)
            # Excluir el usuario actual de los supervisores
            if usuario_actual_id:
                gerentes = gerentes.exclude(usuario_id=usuario_actual_id)
            supervisores = [
                {
                    'id': gerente.id,
                    'nombre': f"{gerente.usuario.get_full_name() or gerente.usuario.username} - Gerente de Equipo"
                }
                for gerente in gerentes
            ]
        elif rol == 'team_leader':
            # Para team leaders, los jefes directos son los jefes de venta del equipo
            jefes = JefeVenta.objects.filter(gerente_equipo__equipo_venta=equipo, activo=True)
            # Excluir el usuario actual de los supervisores
            if usuario_actual_id:
                jefes = jefes.exclude(usuario_id=usuario_actual_id)
            supervisores = [
                {
                    'id': jefe.id,
                    'nombre': f"{jefe.usuario.get_full_name() or jefe.usuario.username} - Jefe de Venta"
                }
                for jefe in jefes
            ]
        elif rol == 'vendedor':
            # Para vendedores, los jefes directos son los team leaders del equipo
            team_leaders = TeamLeader.objects.filter(jefe_venta__gerente_equipo__equipo_venta=equipo, activo=True)
            # Excluir el usuario actual de los supervisores
            if usuario_actual_id:
                team_leaders = team_leaders.exclude(usuario_id=usuario_actual_id)
            supervisores = [
                {
                    'id': tl.id,
                    'nombre': f"{tl.usuario.get_full_name() or tl.usuario.username} - Team Leader"
                }
                for tl in team_leaders
            ]
    
    except EquipoVenta.DoesNotExist:
        advertencia = "Equipo no encontrado."
    
    return JsonResponse({'supervisores': supervisores, 'advertencia': advertencia})


@login_required
def ajax_verificar_subordinados(request):
    """Verificar si un miembro tiene subordinados y devolver información para el reemplazo"""
    member_id = request.GET.get('member_id')
    rol = request.GET.get('rol')
    
    if not member_id or not rol:
        return JsonResponse({'error': 'Parámetros faltantes'}, status=400)
    
    try:
        # Obtener el miembro actual
        miembro_actual, usuario, equipo_actual = get_member_by_role(member_id, rol)
        if not miembro_actual:
            return JsonResponse({'error': 'Miembro no encontrado'}, status=404)
        
        # Verificar subordinados según el rol
        has_subordinados = False
        subordinados_info = []
        replacements = []
        
        if rol == 'gerente':
            # Verificar jefes de venta
            subordinados = miembro_actual.jefeventas.filter(activo=True)
            has_subordinados = subordinados.exists()
            
            if has_subordinados:
                subordinados_info = [
                    {
                        'nombre': jefe.usuario.get_full_name() or jefe.usuario.username,
                        'email': jefe.usuario.email,
                        'rol': 'Jefe de Venta'
                    }
                    for jefe in subordinados
                ]
                
                # Buscar reemplazos posibles: otros gerentes activos del mismo equipo
                posibles_reemplazos = GerenteEquipo.objects.filter(
                    equipo_venta=equipo_actual,
                    activo=True
                ).exclude(id=miembro_actual.id)
                
                # Si no hay en el mismo equipo, buscar en otros equipos
                if not posibles_reemplazos.exists():
                    posibles_reemplazos = GerenteEquipo.objects.filter(
                        activo=True
                    ).exclude(id=miembro_actual.id)
                
                replacements = [
                    {
                        'id': gerente.id,
                        'nombre': gerente.usuario.get_full_name() or gerente.usuario.username,
                        'email': gerente.usuario.email,
                        'tipo': f'Gerente - {gerente.equipo_venta.nombre}'
                    }
                    for gerente in posibles_reemplazos
                ]
        
        elif rol == 'jefe':
            # Verificar team leaders
            subordinados = miembro_actual.teamleaders.filter(activo=True)
            has_subordinados = subordinados.exists()
            
            if has_subordinados:
                subordinados_info = [
                    {
                        'nombre': tl.usuario.get_full_name() or tl.usuario.username,
                        'email': tl.usuario.email,
                        'rol': 'Team Leader'
                    }
                    for tl in subordinados
                ]
                
                # Buscar reemplazos posibles: otros jefes activos del mismo equipo
                posibles_reemplazos = JefeVenta.objects.filter(
                    gerente_equipo__equipo_venta=equipo_actual,
                    activo=True
                ).exclude(id=miembro_actual.id)
                
                # Si no hay en el mismo equipo, buscar en otros equipos
                if not posibles_reemplazos.exists():
                    posibles_reemplazos = JefeVenta.objects.filter(
                        activo=True
                    ).exclude(id=miembro_actual.id)
                
                replacements = [
                    {
                        'id': jefe.id,
                        'nombre': jefe.usuario.get_full_name() or jefe.usuario.username,
                        'email': jefe.usuario.email,
                        'tipo': f'Jefe de Venta - {jefe.gerente_equipo.equipo_venta.nombre}'
                    }
                    for jefe in posibles_reemplazos
                ]
        
        elif rol == 'team_leader':
            # Verificar vendedores
            subordinados = miembro_actual.vendedores.filter(activo=True)
            has_subordinados = subordinados.exists()
            
            if has_subordinados:
                subordinados_info = [
                    {
                        'nombre': vendedor.usuario.get_full_name() or vendedor.usuario.username,
                        'email': vendedor.usuario.email,
                        'rol': 'Vendedor'
                    }
                    for vendedor in subordinados
                ]
                
                # Buscar reemplazos posibles: otros team leaders activos del mismo equipo
                posibles_reemplazos = TeamLeader.objects.filter(
                    jefe_venta__gerente_equipo__equipo_venta=equipo_actual,
                    activo=True
                ).exclude(id=miembro_actual.id)
                
                # Si no hay en el mismo equipo, buscar en otros equipos
                if not posibles_reemplazos.exists():
                    posibles_reemplazos = TeamLeader.objects.filter(
                        activo=True
                    ).exclude(id=miembro_actual.id)
                
                replacements = [
                    {
                        'id': tl.id,
                        'nombre': tl.usuario.get_full_name() or tl.usuario.username,
                        'email': tl.usuario.email,
                        'tipo': f'Team Leader - {tl.jefe_venta.gerente_equipo.equipo_venta.nombre}'
                    }
                    for tl in posibles_reemplazos
                ]
        
        # Los vendedores no tienen subordinados
        elif rol == 'vendedor':
            has_subordinados = False
        
        return JsonResponse({
            'has_subordinados': has_subordinados,
            'subordinados': subordinados_info,
            'replacements': replacements
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)