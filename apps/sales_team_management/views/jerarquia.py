# apps/sales_team_management/views/jerarquia.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse

from ..models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    ComisionVenta, SupervisionDirecta
)
from apps.real_estate_projects.models import (
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    ComisionDesarrollo, AsignacionEquipoProyecto
)
from ..forms import (
    EquipoVentaForm, GerenteEquipoForm, MiembroEquipoForm, ProyectoForm, InmuebleForm,
    ComisionDesarrolloForm, ComisionVentaForm, EquipoVentaFilterForm,
    ProyectoFilterForm
)
from .helpers import get_member_by_role


def get_supervisor_real(usuario, objeto, rol_key):
    """
    Obtiene el supervisor real de un usuario considerando supervisi贸n directa
    """
    # Verificar si tiene supervisi贸n directa activa
    supervision_directa = SupervisionDirecta.objects.filter(
        subordinado=usuario, 
        activo=True
    ).first()
    
    if supervision_directa:
        return {
            'supervisor': supervision_directa.supervisor.get_full_name() or supervision_directa.supervisor.username,
            'es_supervision_directa': True,
            'tipo_supervision': supervision_directa.get_tipo_supervision_display()
        }
    
    # Si no hay supervisi贸n directa, usar jerarqu铆a normal
    supervisor_info = {
        'supervisor': None,
        'es_supervision_directa': False,
        'tipo_supervision': None
    }
    
    if rol_key == 'jefe' and hasattr(objeto, 'gerente_equipo'):
        supervisor_info['supervisor'] = objeto.gerente_equipo.usuario.get_full_name() or objeto.gerente_equipo.usuario.username
    elif rol_key == 'team_leader' and hasattr(objeto, 'jefe_venta'):
        supervisor_info['supervisor'] = objeto.jefe_venta.usuario.get_full_name() or objeto.jefe_venta.usuario.username
    elif rol_key == 'vendedor' and hasattr(objeto, 'team_leader'):
        supervisor_info['supervisor'] = objeto.team_leader.usuario.get_full_name() or objeto.team_leader.usuario.username
    
    return supervisor_info


@login_required
@permission_required('sales_team_management.view_equipoventa', raise_exception=True)
def jerarquia_equipos_list(request):
    """Lista de jerarquía de equipos con filtros por equipo y rol"""
    
    # Filtros
    equipo_id = request.GET.get('equipo')
    rol = request.GET.get('rol')
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
        # Gerentes (mostrar activos)
        for gerente in equipo.gerenteequipo_set.filter(activo=True):
            
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
            
            # Jefes de Venta bajo este gerente (activos O con supervisión directa)
            jefes_query = gerente.jefeventas.filter(activo=True)
            # Agregar jefes con supervisión directa activa aunque estén inactivos en jerarquía
            jefes_supervision_directa = gerente.jefeventas.filter(
                usuario__supervisores_directos__activo=True
            ).exclude(activo=True)
            
            todos_los_jefes = jefes_query.union(jefes_supervision_directa)
            
            for jefe in todos_los_jefes:
                
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
                    
                    # Obtener supervisor real
                    supervisor_info = get_supervisor_real(usuario_jefe, jefe, 'jefe')
                    
                    miembros.append({
                        'equipo': equipo,
                        'usuario': usuario_jefe,
                        'rol': 'Jefe de Venta',
                        'rol_key': 'jefe',
                        'activo': jefe.activo,
                        'fecha_asignacion': jefe.created_at,
                        'supervisor': supervisor_info['supervisor'],
                        'es_supervision_directa': supervisor_info['es_supervision_directa'],
                        'tipo_supervision': supervisor_info['tipo_supervision'],
                        'objeto': jefe,
                        'puede_eliminar': puede_eliminar_jefe
                    })
                
                # Team Leaders bajo este jefe (activos O con supervisión directa)
                tl_query = jefe.teamleaders.filter(activo=True)
                # Agregar TL con supervisión directa activa aunque estén inactivos en jerarquía
                tl_supervision_directa = jefe.teamleaders.filter(
                    usuario__supervisores_directos__activo=True
                ).exclude(activo=True)
                
                todos_los_tl = tl_query.union(tl_supervision_directa)
                
                for team_leader in todos_los_tl:
                    
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
                        
                        # Obtener supervisor real
                        supervisor_info = get_supervisor_real(usuario_tl, team_leader, 'team_leader')
                        
                        miembros.append({
                            'equipo': equipo,
                            'usuario': usuario_tl,
                            'rol': 'Team Leader',
                            'rol_key': 'team_leader',
                            'activo': team_leader.activo,
                            'fecha_asignacion': team_leader.created_at,
                            'supervisor': supervisor_info['supervisor'],
                            'es_supervision_directa': supervisor_info['es_supervision_directa'],
                            'tipo_supervision': supervisor_info['tipo_supervision'],
                            'objeto': team_leader,
                            'puede_eliminar': puede_eliminar_tl
                        })
                    
                    # Vendedores bajo este team leader (activos O con supervisión directa)
                    vendedores_query = team_leader.vendedores.filter(activo=True)
                    # Agregar vendedores con supervisión directa activa aunque estén inactivos en jerarquía
                    vendedores_supervision_directa = team_leader.vendedores.filter(
                        usuario__supervisores_directos__activo=True
                    ).exclude(activo=True)
                    
                    todos_los_vendedores = vendedores_query.union(vendedores_supervision_directa)
                    
                    for vendedor in todos_los_vendedores:
                        
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
                            
                            # Obtener supervisor real
                            supervisor_info = get_supervisor_real(usuario_v, vendedor, 'vendedor')
                            
                            miembros.append({
                                'equipo': equipo,
                                'usuario': usuario_v,
                                'rol': 'Vendedor',
                                'rol_key': 'vendedor',
                                'activo': vendedor.activo,
                                'fecha_asignacion': vendedor.created_at,
                                'supervisor': supervisor_info['supervisor'],
                                'es_supervision_directa': supervisor_info['es_supervision_directa'],
                                'tipo_supervision': supervisor_info['tipo_supervision'],
                                'objeto': vendedor,
                                'puede_eliminar': puede_eliminar_v
                            })
    
    # Agregar usuarios con supervisión directa que no aparecieron en la jerarquía normal
    # (usuarios que pueden estar inactivos en jerarquía pero activos en supervisión directa)
    from ..models import SupervisionDirecta
    
    supervisiones_activas = SupervisionDirecta.objects.filter(
        activo=True,
        equipo_venta__in=equipos_filtrados
    ).select_related('subordinado', 'supervisor', 'equipo_venta')
    
    # IDs de usuarios ya agregados para evitar duplicados
    usuarios_ya_agregados = {miembro['usuario'].id for miembro in miembros}
    
    for supervision in supervisiones_activas:
        usuario = supervision.subordinado
        equipo = supervision.equipo_venta
        
        # Solo agregar si no está ya en la lista
        if usuario.id not in usuarios_ya_agregados:
            # Determinar el rol basado en el tipo de supervisión
            rol_map = {
                'GERENTE_TO_VENDEDOR': ('vendedor', 'Vendedor'),
                'GERENTE_TO_TEAMLEADER': ('team_leader', 'Team Leader'),
                'JEFE_TO_VENDEDOR': ('vendedor', 'Vendedor'),
            }
            
            if supervision.tipo_supervision in rol_map:
                rol_key, rol_display = rol_map[supervision.tipo_supervision]
                
                # Aplicar filtro de rol si existe
                if rol and rol != 'todos' and rol != rol_key:
                    continue
                
                # Aplicar filtro de búsqueda
                if search:
                    search_lower = search.lower()
                    nombre_completo = usuario.get_full_name() or ""
                    nombre_lower = nombre_completo.lower()
                    username_lower = usuario.username.lower()
                    email_lower = (usuario.email or "").lower()
                    
                    if not (search_lower in nombre_lower or search_lower in username_lower or search_lower in email_lower):
                        continue
                
                # Buscar el objeto real del usuario en la jerarquía para obtener la fecha
                objeto_miembro = None
                fecha_asignacion = supervision.fecha_inicio
                
                if rol_key == 'vendedor':
                    objeto_miembro = Vendedor.objects.filter(usuario=usuario).first()
                elif rol_key == 'team_leader':
                    objeto_miembro = TeamLeader.objects.filter(usuario=usuario).first()
                elif rol_key == 'jefe':
                    objeto_miembro = JefeVenta.objects.filter(usuario=usuario).first()
                
                if objeto_miembro:
                    fecha_asignacion = objeto_miembro.created_at
                
                miembros.append({
                    'equipo': equipo,
                    'usuario': usuario,
                    'rol': rol_display,
                    'rol_key': rol_key,
                    'activo': True,  # Si tiene supervisión directa activa, considerarlo activo
                    'fecha_asignacion': fecha_asignacion,
                    'supervisor': supervision.supervisor.get_full_name() or supervision.supervisor.username,
                    'es_supervision_directa': True,
                    'tipo_supervision': supervision.get_tipo_supervision_display(),
                    'objeto': objeto_miembro,
                    'puede_eliminar': True  # Los usuarios con supervisión directa generalmente se pueden gestionar
                })
                
                usuarios_ya_agregados.add(usuario.id)
    
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
        'search': search,
        'stats': stats,
        'page_size': page_size,
        'page_size_options': [10, 25, 50, 100],
        'title': 'Jerarquía de Equipos',
    }
    return render(request, 'sales_team_management/jerarquia/list.html', context)


@login_required
@permission_required('sales_team_management.add_equipoventa', raise_exception=True)
def jerarquia_create_member(request):
    """Crear/asignar un nuevo miembro a la jerarquía"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario')
        equipo_id = request.POST.get('equipo')
        rol = request.POST.get('rol')
        supervisor_id = request.POST.get('supervisor')
        supervision_directa = request.POST.get('supervision_directa') == '1'  # Nuevo campo
        
        try:
            usuario = User.objects.get(id=usuario_id)
            equipo = EquipoVenta.objects.get(id=equipo_id)
            
            # Si es supervisión directa, manejar de forma diferente
            if supervision_directa and rol != 'gerente':
                return _crear_supervision_directa(request, usuario, equipo, rol, supervisor_id)
            
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
                        return render(request, 'sales_team_management/jerarquia/confirm_replace.html', context)
                    
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
    return render(request, 'sales_team_management/jerarquia/create.html', context)


@login_required
@permission_required('sales_team_management.view_equipoventa', raise_exception=True)
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
            supervisor_info = {'supervisor': None, 'es_supervision_directa': False, 'tipo_supervision': None}
        elif rol == 'jefe':
            miembro = get_object_or_404(JefeVenta, id=member_id)
            equipo = miembro.gerente_equipo.equipo_venta
            usuario = miembro.usuario
            rol_display = 'Jefe de Venta'
            supervisor_info = get_supervisor_real(usuario, miembro, 'jefe')
        elif rol == 'team_leader':
            miembro = get_object_or_404(TeamLeader, id=member_id)
            equipo = miembro.jefe_venta.gerente_equipo.equipo_venta
            usuario = miembro.usuario
            rol_display = 'Team Leader'
            supervisor_info = get_supervisor_real(usuario, miembro, 'team_leader')
        elif rol == 'vendedor':
            miembro = get_object_or_404(Vendedor, id=member_id)
            equipo = miembro.team_leader.jefe_venta.gerente_equipo.equipo_venta
            usuario = miembro.usuario
            rol_display = 'Vendedor'
            supervisor_info = get_supervisor_real(usuario, miembro, 'vendedor')
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
            'supervisor': supervisor_info['supervisor'],
            'es_supervision_directa': supervisor_info['es_supervision_directa'],
            'tipo_supervision': supervisor_info['tipo_supervision'],
            'estadisticas_mes': estadisticas_mes,
            'subordinados_count': subordinados_count,
            'subordinados_tipo': subordinados_tipo,
            'mes_actual': hoy.strftime('%B %Y'),
            'title': f'{rol_display}: {usuario.get_full_name() or usuario.username}',
        }
        
        return render(request, 'sales_team_management/jerarquia/detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar detalles: {str(e)}')
        return redirect('sales:jerarquia_list')


def update_user_info(request, usuario):
    """Helper function to update user information from form data"""
    from django.contrib.auth import get_user_model
    from datetime import datetime, date
    
    User = get_user_model()
    
    # Campos básicos
    usuario.first_name = request.POST.get('first_name', '').strip()
    usuario.last_name = request.POST.get('last_name', '').strip()
    usuario.email = request.POST.get('email', '').strip()
    
    # Nuevos campos
    cedula = request.POST.get('cedula', '').strip()
    fecha_nacimiento = request.POST.get('fecha_nacimiento', '').strip()
    domicilio = request.POST.get('domicilio', '').strip()
    latitud = request.POST.get('latitud', '').strip()
    longitud = request.POST.get('longitud', '').strip()
    
    # Validar y asignar cédula
    if cedula:
        # Verificar que no esté en uso por otro usuario
        if User.objects.filter(cedula=cedula).exclude(id=usuario.id).exists():
            return False, 'Ya existe un usuario con esta cédula.'
        usuario.cedula = cedula
    else:
        usuario.cedula = None
    
    # Validar y asignar fecha de nacimiento
    if fecha_nacimiento:
        try:
            fecha_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
            
            # Verificar que la fecha sea válida
            today = date.today()
            if fecha_obj > today:
                return False, 'La fecha de nacimiento no puede ser en el futuro.'
            elif today.year - fecha_obj.year > 120:
                return False, 'La fecha de nacimiento no puede ser mayor a 120 años.'
            
            usuario.fecha_nacimiento = fecha_obj
        except ValueError:
            return False, 'Formato de fecha inválido.'
    else:
        usuario.fecha_nacimiento = None
    
    # Asignar domicilio
    usuario.domicilio = domicilio if domicilio else None
    
    # Validar y asignar coordenadas
    if latitud and longitud:
        try:
            lat_decimal = float(latitud)
            lng_decimal = float(longitud)
            
            # Validar rangos
            if not (-90 <= lat_decimal <= 90):
                return False, 'La latitud debe estar entre -90 y 90.'
            if not (-180 <= lng_decimal <= 180):
                return False, 'La longitud debe estar entre -180 y 180.'
            
            usuario.latitud = lat_decimal
            usuario.longitud = lng_decimal
        except ValueError:
            return False, 'Las coordenadas deben ser números válidos.'
    else:
        usuario.latitud = None
        usuario.longitud = None
    
    # Validar email único
    if User.objects.filter(email=usuario.email).exclude(id=usuario.id).exists():
        return False, 'Ya existe un usuario con este email.'
    
    # Guardar cambios del usuario
    usuario.save()
    return True, 'Usuario actualizado exitosamente.'


@login_required
@permission_required('sales_team_management.change_equipoventa', raise_exception=True)
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
            supervision_directa = request.POST.get('supervision_directa') == '1'
            activo = request.POST.get('activo') == 'on'
            accion = request.POST.get('accion', 'editar')  # 'editar' o 'inactivar'
            reemplazo_id = request.POST.get('reemplazo')
            
            # MANEJO SIMPLIFICADO DE SUPERVISIÓN DIRECTA EN EDICIÓN
            if supervision_directa and nuevo_supervisor_id and rol != 'gerente':
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    usuario = miembro.usuario
                    supervisor_usuario = User.objects.get(id=nuevo_supervisor_id)
                    
                    # Desactivar cualquier supervisión directa anterior
                    SupervisionDirecta.objects.filter(subordinado=usuario, activo=True).update(activo=False)
                    
                    # Determinar tipo de supervisión
                    # Obtener rol del supervisor
                    supervisor_rol = None
                    if GerenteEquipo.objects.filter(usuario=supervisor_usuario, activo=True).exists():
                        supervisor_rol = 'gerente'
                    elif JefeVenta.objects.filter(usuario=supervisor_usuario, activo=True).exists():
                        supervisor_rol = 'jefe'
                    elif TeamLeader.objects.filter(usuario=supervisor_usuario, activo=True).exists():
                        supervisor_rol = 'team_leader'
                    
                    # Determinar tipo de supervisión según roles
                    tipo_supervision = None
                    if supervisor_rol == 'gerente' and rol == 'vendedor':
                        tipo_supervision = 'GERENTE_TO_VENDEDOR'
                    elif supervisor_rol == 'gerente' and rol == 'team_leader':
                        tipo_supervision = 'GERENTE_TO_TEAMLEADER'
                    elif supervisor_rol == 'jefe' and rol == 'vendedor':
                        tipo_supervision = 'JEFE_TO_VENDEDOR'
                    
                    if tipo_supervision:
                        # Crear nueva supervisión directa
                        SupervisionDirecta.objects.create(
                            supervisor=supervisor_usuario,
                            subordinado=usuario,
                            equipo_venta=equipo_actual,
                            tipo_supervision=tipo_supervision,
                            activo=True
                        )
                        
                        messages.success(request, f'Supervisión directa actualizada exitosamente.')
                        return redirect('sales:jerarquia_member_detail', member_id=member_id, rol=rol)
                        
                except Exception as e:
                    messages.error(request, f'Error al actualizar supervisión directa: {str(e)}')
            
            elif not supervision_directa and rol != 'gerente':
                # Si se desactivó supervisión directa, desactivar registros existentes
                SupervisionDirecta.objects.filter(subordinado=miembro.usuario, activo=True).update(activo=False)
                # Aquí deberías actualizar la jerarquía normal, pero es complejo
                messages.success(request, f'Supervisión directa desactivada. Actualiza el supervisor en jerarquía normal.')
                return redirect('sales:jerarquia_member_detail', member_id=member_id, rol=rol)
            
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
                    return render(request, 'sales_team_management/jerarquia/confirm_inactivate.html', context)
                
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
                            return render(request, 'sales_team_management/jerarquia/confirm_reactivate.html', context)
                        
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
                    
                    # Actualizar información del usuario (para gerentes)
                    success, message = update_user_info(request, miembro.usuario)
                    if not success:
                        messages.error(request, message)
                        return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
                    
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
                
                # Actualizar información del usuario
                success, message = update_user_info(request, miembro.usuario)
                if not success:
                    messages.error(request, message)
                    return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
                
                messages.success(request, f'Usuario actualizado exitosamente.')
                return redirect('sales:jerarquia_list')
                
            except Exception as e:
                messages.error(request, f'Error al actualizar: {str(e)}')
                return redirect('sales:jerarquia_member_edit', member_id=member_id, rol=rol)
        
        # GET request - mostrar formulario
        equipos = EquipoVenta.objects.filter(activo=True).order_by('nombre')
        
        # Obtener el usuario del miembro
        usuario = miembro.usuario
        
        # Obtener información de supervisor actual
        if rol != 'gerente':
            supervisor_info = get_supervisor_real(usuario, miembro, rol)
            # Obtener el ID del supervisor actual para pre-seleccionarlo
            supervisor_actual_id = None
            if supervisor_info['es_supervision_directa']:
                # Si es supervisión directa, buscar en SupervisionDirecta
                supervision_directa = SupervisionDirecta.objects.filter(
                    subordinado=usuario, activo=True
                ).first()
                if supervision_directa:
                    supervisor_actual_id = supervision_directa.supervisor.id
            else:
                # Si es jerarquía normal, obtener el ID del supervisor según el rol
                if rol == 'jefe' and hasattr(miembro, 'gerente_equipo'):
                    supervisor_actual_id = miembro.gerente_equipo.id
                elif rol == 'team_leader' and hasattr(miembro, 'jefe_venta'):
                    supervisor_actual_id = miembro.jefe_venta.id
                elif rol == 'vendedor' and hasattr(miembro, 'team_leader'):
                    supervisor_actual_id = miembro.team_leader.id
        else:
            supervisor_info = {'es_supervision_directa': False}
            supervisor_actual_id = None
        
        context = {
            'miembro': miembro,
            'rol': rol,
            'rol_display': rol.replace('_', ' ').title(),
            'equipo_actual': equipo_actual,
            'equipos': equipos,
            'es_supervision_directa': supervisor_info['es_supervision_directa'],
            'supervisor_actual_id': supervisor_actual_id,
            'title': f'Editar {rol.replace("_", " ").title()}',
        }
        
        return render(request, 'sales_team_management/jerarquia/edit.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar datos: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales_team_management.delete_equipoventa', raise_exception=True)
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
        
        return render(request, 'sales_team_management/jerarquia/delete.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar datos: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales_team_management.change_equipoventa', raise_exception=True)
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
                        return render(request, 'sales_team_management/jerarquia/confirm_reassign.html', context)
                    
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
        
        return render(request, 'sales_team_management/jerarquia/reassign.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar datos: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales_team_management.change_gerenteequipo', raise_exception=True)
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
        
        return render(request, 'sales_team_management/jerarquia/deactivate.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al procesar solicitud: {str(e)}')
        return redirect('sales:jerarquia_list')


@login_required
@permission_required('sales_team_management.change_gerenteequipo', raise_exception=True)
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


def _crear_supervision_directa(request, usuario, equipo, rol, supervisor_id):
    """
    Función auxiliar para crear supervisión directa
    """
    from django.contrib.auth import get_user_model
    from ..models import SupervisionDirecta
    
    User = get_user_model()
    
    try:
        # Obtener el supervisor
        supervisor = User.objects.get(id=supervisor_id)
        
        # Primero crear la relación jerárquica normal (necesaria para que el usuario esté en el equipo)
        if rol == 'jefe':
            # Para jefe de venta, necesita un gerente como supervisor normal
            # Buscar un gerente del equipo (puede ser cualquiera)
            gerente_default = GerenteEquipo.objects.filter(equipo_venta=equipo, activo=True).first()
            if not gerente_default:
                messages.error(request, 'El equipo necesita al menos un gerente activo para crear supervisión directa.')
                return redirect('sales:jerarquia_create_member')
            
            # Verificar si ya existe
            if JefeVenta.objects.filter(usuario=usuario, gerente_equipo=gerente_default).exists():
                messages.error(request, f'{usuario.get_full_name() or usuario.username} ya es jefe de venta en este equipo.')
                return redirect('sales:jerarquia_create_member')
            
            # Crear la relacion normal
            miembro_creado = JefeVenta.objects.create(usuario=usuario, gerente_equipo=gerente_default)
            
        elif rol == 'team_leader':
            # Para team leader, necesita un jefe de venta como supervisor normal
            jefe_default = JefeVenta.objects.filter(gerente_equipo__equipo_venta=equipo, activo=True).first()
            if not jefe_default:
                messages.error(request, 'El equipo necesita al menos un jefe de venta activo para crear supervisión directa.')
                return redirect('sales:jerarquia_create_member')
            
            # Verificar si ya existe
            if TeamLeader.objects.filter(usuario=usuario, jefe_venta=jefe_default).exists():
                messages.error(request, f'{usuario.get_full_name() or usuario.username} ya es team leader en este equipo.')
                return redirect('sales:jerarquia_create_member')
            
            # Crear la relacion normal
            miembro_creado = TeamLeader.objects.create(usuario=usuario, jefe_venta=jefe_default)
            
        elif rol == 'vendedor':
            # Para vendedor con supervisión directa, crear estructuras temporales mínimas si no existen
            tl_default = TeamLeader.objects.filter(jefe_venta__gerente_equipo__equipo_venta=equipo, activo=True).first()
            
            if not tl_default:
                # Si no hay team leader, buscar o crear un jefe de venta temporal
                jefe_default = JefeVenta.objects.filter(gerente_equipo__equipo_venta=equipo, activo=True).first()
                
                if not jefe_default:
                    # Si no hay jefe de venta, crear uno temporal usando el gerente
                    gerente_default = GerenteEquipo.objects.filter(equipo_venta=equipo, activo=True).first()
                    if not gerente_default:
                        messages.error(request, 'El equipo necesita al menos un gerente activo para crear supervisión directa.')
                        return redirect('sales:jerarquia_create_member')
                    
                    # Crear jefe de venta temporal
                    jefe_default = JefeVenta.objects.create(
                        usuario=gerente_default.usuario,  # Usar el mismo usuario del gerente temporalmente
                        gerente_equipo=gerente_default,
                        activo=False  # Marcarlo como inactivo ya que es temporal
                    )
                
                # Crear team leader temporal
                tl_default = TeamLeader.objects.create(
                    usuario=jefe_default.usuario,  # Usar el mismo usuario del jefe temporalmente
                    jefe_venta=jefe_default,
                    activo=False  # Marcarlo como inactivo ya que es temporal
                )
            
            # Verificar si ya existe
            if Vendedor.objects.filter(usuario=usuario, team_leader=tl_default).exists():
                messages.error(request, f'{usuario.get_full_name() or usuario.username} ya es vendedor en este equipo.')
                return redirect('sales:jerarquia_create_member')
            
            # Crear la relacion normal (que será ignorada por la supervisión directa)
            miembro_creado = Vendedor.objects.create(usuario=usuario, team_leader=tl_default)
        
        # Determinar el tipo de supervisión directa
        supervisor_rol = _get_rol_usuario_en_equipo(supervisor, equipo)
        subordinado_rol = rol.upper()
        
        tipo_supervision = None
        if supervisor_rol == 'GERENTE' and subordinado_rol == 'VENDEDOR':
            tipo_supervision = 'GERENTE_TO_VENDEDOR'
        elif supervisor_rol == 'GERENTE' and subordinado_rol == 'TEAM_LEADER':
            tipo_supervision = 'GERENTE_TO_TEAMLEADER'
        elif supervisor_rol == 'JEFE' and subordinado_rol == 'VENDEDOR':
            tipo_supervision = 'JEFE_TO_VENDEDOR'
        else:
            messages.error(request, f'Tipo de supervisión directa no válido: {supervisor_rol} → {subordinado_rol}')
            return redirect('sales:jerarquia_create_member')
        
        # Verificar que no existe ya una supervisión directa activa
        supervision_existente = SupervisionDirecta.objects.filter(
            subordinado=usuario,
            equipo_venta=equipo,
            activo=True
        ).first()
        
        if supervision_existente:
            messages.error(request, f'{usuario.get_full_name() or usuario.username} ya tiene supervisión directa activa con {supervision_existente.supervisor.get_full_name()}.')
            return redirect('sales:jerarquia_create_member')
        
        # Crear la supervisión directa
        SupervisionDirecta.objects.create(
            supervisor=supervisor,
            subordinado=usuario,
            equipo_venta=equipo,
            tipo_supervision=tipo_supervision,
            activo=True,
            notas=f'Supervisión directa creada desde formulario de jerarquía: {supervisor.get_full_name()} supervisa directamente a {usuario.get_full_name()}'
        )
        
        messages.success(
            request,
            f'✨ {usuario.get_full_name() or usuario.username} asignado con SUPERVISIÓN DIRECTA: '
            f'{supervisor.get_full_name()} → {usuario.get_full_name()} ({tipo_supervision.replace("_", " → ")})'
        )
        
        return redirect('sales:jerarquia_list')
        
    except User.DoesNotExist:
        messages.error(request, 'Supervisor no encontrado.')
        return redirect('sales:jerarquia_create_member')
    except Exception as e:
        messages.error(request, f'Error al crear supervisión directa: {str(e)}')
        return redirect('sales:jerarquia_create_member')


def _get_rol_usuario_en_equipo(usuario, equipo):
    """
    Obtiene el rol de un usuario en un equipo específico
    """
    # Verificar cada nivel de jerarquía
    if GerenteEquipo.objects.filter(usuario=usuario, equipo_venta=equipo, activo=True).exists():
        return 'GERENTE'
    
    if JefeVenta.objects.filter(usuario=usuario, gerente_equipo__equipo_venta=equipo, activo=True).exists():
        return 'JEFE'
    
    if TeamLeader.objects.filter(usuario=usuario, jefe_venta__gerente_equipo__equipo_venta=equipo, activo=True).exists():
        return 'TEAM_LEADER'
    
    if Vendedor.objects.filter(usuario=usuario, team_leader__jefe_venta__gerente_equipo__equipo_venta=equipo, activo=True).exists():
        return 'VENDEDOR'
    
    return 'DESCONOCIDO'