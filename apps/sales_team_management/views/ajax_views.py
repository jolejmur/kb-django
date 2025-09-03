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

# Nuevos modelos
from ..models import (
    OrganizationalUnit, PositionType, TeamMembership, HierarchyRelation
)
from apps.real_estate_projects.models import (
    Proyecto, Inmueble
)

User = get_user_model()


# ============================================================
# FUNCIONES HELPER ACTUALIZADAS PARA NUEVO MODELO
# ============================================================

def get_membership_by_id(membership_id):
    """
    Función helper para obtener una membresía de equipo
    Retorna: (membership, usuario, equipo)
    """
    try:
        membership = TeamMembership.objects.select_related(
            'user', 'organizational_unit', 'position_type'
        ).get(id=membership_id, is_active=True)
        
        return membership, membership.user, membership.organizational_unit
        
    except TeamMembership.DoesNotExist:
        return None, None, None


# ============================================================
# VISTAS AJAX ACTUALIZADAS
# ============================================================

@login_required
def ajax_equipos_search(request):
    """Búsqueda AJAX de equipos para autocompletado"""
    query = request.GET.get('q', '')
    equipos = OrganizationalUnit.objects.filter(
        name__icontains=query,
        is_active=True
    ).values('id', 'name')[:10]

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
def ajax_search_users(request):
    """Búsqueda AJAX de usuarios para el widget de selección"""
    query = request.GET.get('q', '').strip()
    
    # Obtener usuarios que ya están asignados a equipos usando el nuevo modelo
    usuarios_ocupados = set()
    
    # Usuarios que ya tienen membresías activas en cualquier equipo
    usuarios_ocupados.update(
        TeamMembership.objects.filter(is_active=True).values_list('user_id', flat=True)
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
def ajax_create_user(request):
    # Verificar que el usuario tenga acceso al módulo "Jerarquía de Equipos"
    if not request.user.has_module_access('Jerarquía de Equipos'):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
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
        telefono = request.POST.get('telefono', '').strip()
        fecha_nacimiento = request.POST.get('fecha_nacimiento', '').strip()
        domicilio = request.POST.get('domicilio', '').strip()
        latitud = request.POST.get('latitud', '').strip()
        longitud = request.POST.get('longitud', '').strip()
        foto_perfil = request.FILES.get('foto_perfil')
        
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
        
        # Validar foto de perfil
        if foto_perfil:
            # Validar tamaño (máximo 5MB)
            if foto_perfil.size > 5 * 1024 * 1024:
                errors['foto_perfil'] = 'La imagen no puede ser mayor a 5MB'
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if foto_perfil.content_type not in allowed_types:
                errors['foto_perfil'] = 'Solo se permiten archivos JPG, PNG o GIF'
        
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
        if telefono:
            user.telefono = telefono
        if fecha_nacimiento:
            user.fecha_nacimiento = fecha_obj
        if domicilio:
            user.domicilio = domicilio
        if lat_decimal is not None and lng_decimal is not None:
            user.latitud = lat_decimal
            user.longitud = lng_decimal
        if foto_perfil:
            user.foto_perfil = foto_perfil
        
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
                'telefono': user.telefono,
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


@login_required
def ajax_search_hierarchy(request):
    """Búsqueda AJAX de jerarquía completa con filtros (incluye todos los miembros, priorizando usuarios inactivos)"""
    try:
        from ..models import HierarchyRelation, OrganizationalUnit, TeamMembership
        from django.template.loader import render_to_string
        from django.core.paginator import Paginator
        
        # ============================================================
        # CONTROL DE ACCESO POR EQUIPO (igual que en la vista principal)
        # ============================================================
        user_membership = TeamMembership.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('organizational_unit', 'position_type').first()
        
        query = request.GET.get('q', '').strip()
        unit_filter = request.GET.get('unit_filter', '').strip()
        
        # Si es miembro de equipo, FORZAR filtro de su equipo
        if user_membership:
            user_team_id = str(user_membership.organizational_unit.id)
            # SEGURIDAD: Verificar que no esté intentando manipular el filtro
            if unit_filter and unit_filter != user_team_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Acceso denegado: No puedes ver información de otros equipos'
                })
            # Aplicar filtro forzado
            unit_filter = user_team_id
        
        page = int(request.GET.get('page', 1))
        
        # Obtener page_size de los parámetros GET
        page_size = request.GET.get('page_size', '10')
        try:
            page_size = int(page_size)
            if page_size not in [10, 20, 50]:
                page_size = 10
        except (ValueError, TypeError):
            page_size = 10
        
        # Obtener todas las membresías activas E INACTIVAS (para incluir usuarios públicos)
        memberships = TeamMembership.objects.select_related(
            'user',
            'position_type',
            'organizational_unit'
        ).order_by(
            'user__is_active',  # Usuarios inactivos primero (False < True)
            'is_active',        # Membresías inactivas primero
            'organizational_unit__name', 
            'position_type__hierarchy_level'
        )
        
        # Aplicar filtro por equipo si se especifica
        if unit_filter:
            memberships = memberships.filter(organizational_unit_id=unit_filter)
        
        # Aplicar filtro de búsqueda a las membresías
        if query:
            memberships = memberships.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__username__icontains=query) |
                Q(user__email__icontains=query) |
                Q(organizational_unit__name__icontains=query) |
                Q(position_type__name__icontains=query)
            )
        
        # Obtener relaciones jerárquicas existentes (activas e inactivas)
        existing_relations = HierarchyRelation.objects.select_related(
            'supervisor_membership__user',
            'supervisor_membership__position_type',
            'supervisor_membership__organizational_unit',
            'subordinate_membership__user',
            'subordinate_membership__position_type',
            'subordinate_membership__organizational_unit'
        ).order_by(
            'subordinate_membership__user__is_active',  # Usuarios inactivos primero
            'is_active',  # Relaciones inactivas primero
            'created_at'
        )
        
        # Aplicar filtros a las relaciones existentes
        if unit_filter:
            existing_relations = existing_relations.filter(
                Q(supervisor_membership__organizational_unit_id=unit_filter) |
                Q(subordinate_membership__organizational_unit_id=unit_filter)
            )
        
        # Aplicar filtro de búsqueda a las relaciones existentes
        if query:
            existing_relations = existing_relations.filter(
                Q(subordinate_membership__user__first_name__icontains=query) |
                Q(subordinate_membership__user__last_name__icontains=query) |
                Q(subordinate_membership__user__username__icontains=query) |
                Q(subordinate_membership__user__email__icontains=query) |
                Q(subordinate_membership__organizational_unit__name__icontains=query) |
                Q(subordinate_membership__position_type__name__icontains=query)
            )
        
        # Crear un diccionario de relaciones por subordinado
        relations_dict = {}
        for relation in existing_relations:
            subordinate_id = relation.subordinate_membership.id
            relations_dict[subordinate_id] = relation
        
        # Construir lista completa de jerarquía
        all_hierarchy_items = []
        processed_memberships = set()  # Para evitar duplicados
        
        # Primero agregar todas las relaciones explícitas
        for relation in existing_relations:
            all_hierarchy_items.append(relation)
            # Solo marcar subordinados como procesados (ya tienen relación explícita)
            processed_memberships.add(relation.subordinate_membership.id)
        
        # Luego agregar miembros que no están en relaciones explícitas
        for membership in memberships:
            if membership.id not in processed_memberships:
                # Determinar si este miembro debería tener supervisor
                is_top_level = membership.position_type.hierarchy_level == 1  # Gerentes son nivel 1
                
                if is_top_level:
                    # Los gerentes/directores no necesitan supervisor - crear pseudo-relación como "Cabeza de Jerarquía"
                    pseudo_relation = type('PseudoRelation', (), {
                        'id': f'head_{membership.id}',
                        'supervisor_membership': None,
                        'subordinate_membership': membership,
                        'relation_type': 'HEAD',
                        'authority_level': 'FULL',
                        'is_active': membership.is_active,
                        'is_primary': True,
                        'created_at': membership.created_at,
                        'get_relation_type_display': lambda: 'Cabeza de Jerarquía',
                        'pk': f'head_{membership.id}'
                    })()
                    all_hierarchy_items.append(pseudo_relation)
                else:
                    # Otros roles sin supervisor explícito - pueden necesitar asignación
                    pseudo_relation = type('PseudoRelation', (), {
                        'id': f'unassigned_{membership.id}',
                        'supervisor_membership': None,
                        'subordinate_membership': membership,
                        'relation_type': 'UNASSIGNED',
                        'authority_level': 'NONE',
                        'is_active': membership.is_active,
                        'is_primary': False,
                        'created_at': membership.created_at,
                        'get_relation_type_display': lambda: 'Sin Supervisor Asignado',
                        'pk': f'unassigned_{membership.id}'
                    })()
                    all_hierarchy_items.append(pseudo_relation)
        
        # Ordenar para que usuarios inactivos aparezcan primero
        def sort_key(item):
            # Obtener el usuario subordinado
            subordinate_user = item.subordinate_membership.user
            # Prioridad: usuarios inactivos primero (0), luego activos (1)
            user_priority = 0 if not subordinate_user.is_active else 1
            # Sub-prioridad: membresías inactivas primero (0), luego activas (1)
            membership_priority = 0 if not item.subordinate_membership.is_active else 1
            # Tercera prioridad: fecha de creación (más recientes primero para inactivos)
            time_priority = item.created_at
            
            return (user_priority, membership_priority, time_priority)
        
        all_hierarchy_items.sort(key=sort_key)
        
        # Paginación
        paginator = Paginator(all_hierarchy_items, page_size)
        page_obj = paginator.get_page(page)
        
        # Renderizar el contenido HTML
        relations_html = render_to_string('sales_team_management/jerarquia/partials/relations_list.html', {
            'page_obj': page_obj
        }, request=request)
        
        # Renderizar paginación
        pagination_html = render_to_string('sales_team_management/jerarquia/partials/pagination.html', {
            'page_obj': page_obj,
            'search': query,
            'unit_filter': unit_filter,
            'current_page_size': page_size
        }, request=request) if page_obj.has_other_pages() else ''
        
        # Debug temporal
        debug_info = {
            'total_memberships': memberships.count(),
            'total_existing_relations': existing_relations.count(),
            'total_hierarchy_items': len(all_hierarchy_items),
            'active_users_count': len([item for item in all_hierarchy_items if item.subordinate_membership.user.is_active]),
            'inactive_users_count': len([item for item in all_hierarchy_items if not item.subordinate_membership.user.is_active])
        }
        
        return JsonResponse({
            'success': True,
            'relations_html': relations_html,
            'pagination_html': pagination_html,
            'total_results': paginator.count,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'debug': debug_info
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error en la búsqueda: {str(e)}'
        })


@login_required
def ajax_toggle_public_registration(request):
    """Toggle del registro público para una unidad organizacional"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        unit_id = request.POST.get('unit_id')
        enabled = request.POST.get('enabled') == 'true'
        
        unit = get_object_or_404(OrganizationalUnit, id=unit_id)
        
        # Verificar permisos
        if not request.user.has_module_access('Gestión de Equipos'):
            return JsonResponse({
                'success': False, 
                'message': 'No tienes permisos para realizar esta acción'
            })
        
        unit.public_registration_enabled = enabled
        unit.save()
        
        # Generar URL pública si está habilitado
        public_url = None
        if enabled:
            from django.urls import reverse
            public_url = f"https://tmkorban.duckdns.org{reverse('sales_team_management:public_register', kwargs={'unit_code': unit.code})}"
        
        return JsonResponse({
            'success': True,
            'message': f'Registro público {"habilitado" if enabled else "deshabilitado"} para {unit.name}',
            'enabled': enabled,
            'public_url': public_url
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al actualizar configuración: {str(e)}'
        })


@csrf_exempt
def ajax_generate_username(request):
    """Generar username en tiempo real para el formulario público"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        first_name = request.GET.get('first_name', '').strip().title()
        last_name = request.GET.get('last_name', '').strip().title()
        
        if not first_name or not last_name:
            return JsonResponse({
                'success': True,
                'username': '',
                'message': 'Ingresa nombre y apellido para generar usuario'
            })
        
        # Función para generar username (misma lógica que en public_registration.py)
        def generate_username(first_name, last_name):
            # Obtener primera letra del primer nombre
            first_letter = first_name.split()[0][0].lower() if first_name else ''
            # Obtener primer apellido (primera palabra del campo last_name)
            first_surname = last_name.split()[0].lower() if last_name else ''
            # Limpiar caracteres especiales y acentos
            import unicodedata
            first_letter = unicodedata.normalize('NFD', first_letter).encode('ascii', 'ignore').decode('ascii')
            first_surname = unicodedata.normalize('NFD', first_surname).encode('ascii', 'ignore').decode('ascii')
            
            base_username = f"{first_letter}{first_surname}"
            
            # Asegurar unicidad agregando número si es necesario
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            return username, base_username != username  # Retorna si hubo que agregar número
        
        generated_username, has_number = generate_username(first_name, last_name)
        
        return JsonResponse({
            'success': True,
            'username': generated_username,
            'has_number': has_number,
            'message': f'Usuario generado: {generated_username}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al generar usuario: {str(e)}'
        })