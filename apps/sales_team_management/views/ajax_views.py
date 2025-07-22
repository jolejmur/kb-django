# apps/sales_team_management/views/ajax_views.py

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Q, Count
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
import json

from ..models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor
)
from apps.real_estate_projects.models import (
    Proyecto, Inmueble
)

User = get_user_model()


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
# VISTAS AJAX
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


@login_required
def ajax_search_users(request):
    """Búsqueda AJAX de usuarios para el widget de selección"""
    query = request.GET.get('q', '').strip()
    
    # Obtener usuarios que no están asignados a ningún equipo
    usuarios_ocupados = set()
    
    # Usuarios que ya son gerentes en cualquier equipo
    usuarios_ocupados.update(
        GerenteEquipo.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    
    # Usuarios que ya son jefes de venta en cualquier equipo
    usuarios_ocupados.update(
        JefeVenta.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    
    # Usuarios que ya son team leaders en cualquier equipo
    usuarios_ocupados.update(
        TeamLeader.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    
    # Usuarios que ya son vendedores en cualquier equipo
    usuarios_ocupados.update(
        Vendedor.objects.filter(activo=True).values_list('usuario_id', flat=True)
    )
    
    # Filtrar usuarios disponibles
    users_query = User.objects.filter(
        is_active=True
    ).exclude(id__in=usuarios_ocupados)
    
    # Aplicar filtro de búsqueda si se proporciona
    if query:
        users_query = users_query.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )
    
    # Limitar resultados y ordenar
    users_query = users_query.order_by('first_name', 'last_name', 'username')[:20]
    
    # Formatear resultados
    users = []
    for user in users_query:
        full_name = user.get_full_name()
        users.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': full_name if full_name else user.username,
        })
    
    return JsonResponse({
        'success': True,
        'users': users,
        'total': len(users)
    })


@login_required
@permission_required('auth.add_user', raise_exception=True)
def ajax_create_user(request):
    """Crear nuevo usuario via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        # Obtener datos del formulario
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Nuevos campos
        cedula = request.POST.get('cedula', '').strip()
        fecha_nacimiento = request.POST.get('fecha_nacimiento', '').strip()
        domicilio = request.POST.get('domicilio', '').strip()
        latitud = request.POST.get('latitud', '').strip()
        longitud = request.POST.get('longitud', '').strip()
        
        # Validaciones
        errors = {}
        
        if not first_name:
            errors['first_name'] = 'El nombre es requerido'
        
        if not last_name:
            errors['last_name'] = 'El apellido es requerido'
        
        if not email:
            errors['email'] = 'El email es requerido'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = 'Email inválido'
            
            # Verificar unicidad del email
            if User.objects.filter(email=email).exists():
                errors['email'] = 'Ya existe un usuario con este email'
        
        if not username:
            errors['username'] = 'El nombre de usuario es requerido'
        else:
            # Validar formato del username
            import re
            if not re.match(r'^[a-zA-Z0-9._]+$', username):
                errors['username'] = 'El nombre de usuario solo puede contener letras, números, puntos y guiones bajos'
            
            # Verificar unicidad del username
            if User.objects.filter(username=username).exists():
                errors['username'] = 'Ya existe un usuario con este nombre de usuario'
        
        if not password:
            errors['password'] = 'La contraseña es requerida'
        elif len(password) < 6:
            errors['password'] = 'La contraseña debe tener al menos 6 caracteres'
        
        # Validaciones para nuevos campos
        if cedula and User.objects.filter(cedula=cedula).exists():
            errors['cedula'] = 'Ya existe un usuario con esta cédula'
        
        if fecha_nacimiento:
            try:
                from datetime import datetime
                fecha_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
                # Verificar que la fecha sea válida (no futuro, no muy antigua)
                from datetime import date
                today = date.today()
                if fecha_obj > today:
                    errors['fecha_nacimiento'] = 'La fecha de nacimiento no puede ser en el futuro'
                elif today.year - fecha_obj.year > 120:
                    errors['fecha_nacimiento'] = 'La fecha de nacimiento no puede ser mayor a 120 años'
            except ValueError:
                errors['fecha_nacimiento'] = 'Formato de fecha inválido'
        
        # Validar coordenadas
        lat_decimal = None
        lng_decimal = None
        if latitud and longitud:
            try:
                lat_decimal = float(latitud)
                lng_decimal = float(longitud)
                
                # Validar rangos de coordenadas
                if not (-90 <= lat_decimal <= 90):
                    errors['latitud'] = 'La latitud debe estar entre -90 y 90'
                if not (-180 <= lng_decimal <= 180):
                    errors['longitud'] = 'La longitud debe estar entre -180 y 180'
            except ValueError:
                errors['coordenadas'] = 'Las coordenadas deben ser números válidos'
        elif latitud or longitud:
            errors['coordenadas'] = 'Debes proporcionar tanto latitud como longitud'
        
        # Si hay errores, retornarlos
        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors
            })
        
        # Crear el usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Agregar los nuevos campos
        if cedula:
            user.cedula = cedula
        if fecha_nacimiento:
            user.fecha_nacimiento = fecha_obj
        if domicilio:
            user.domicilio = domicilio
        if lat_decimal is not None and lng_decimal is not None:
            user.latitud = lat_decimal
            user.longitud = lng_decimal
        
        user.save()
        
        # Retornar el usuario creado
        return JsonResponse({
            'success': True,
            'message': f'Usuario {user.get_full_name() or user.username} creado exitosamente',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() if user.get_full_name() else user.username,
                'cedula': user.cedula,
                'fecha_nacimiento': user.fecha_nacimiento.isoformat() if user.fecha_nacimiento else None,
                'domicilio': user.domicilio,
                'latitud': float(user.latitud) if user.latitud else None,
                'longitud': float(user.longitud) if user.longitud else None,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al crear el usuario: {str(e)}'
        })