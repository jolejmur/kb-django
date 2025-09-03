# apps/sales_team_management/views/jerarquia_new.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.db import models
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from django import forms
from ..decorators_modules import hierarchy_module_required

# NUEVO MODELO - Sin Legacy
from ..models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)
from apps.accounts.models import User


# ============================================================
# FORMS PARA MANEJO DE JERARQUÍAS
# ============================================================

class HierarchyRelationForm(forms.ModelForm):
    """Form para crear/editar relaciones jerárquicas"""
    class Meta:
        model = HierarchyRelation
        fields = ['relation_type', 'authority_level', 'justification', 'is_primary']
        widgets = {
            'relation_type': forms.Select(attrs={'class': 'form-control'}),
            'authority_level': forms.Select(attrs={'class': 'form-control'}),
            'justification': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


# ============================================================
# VISTAS DE JERARQUÍA ACTUALIZADAS
# ============================================================



@login_required
@hierarchy_module_required
def jerarquia_list(request):
    """Lista completa de jerarquía organizacional incluyendo todos los miembros"""
    
    # ============================================================
    # CONTROL DE ACCESO POR EQUIPO
    # ============================================================
    user_team = None
    is_team_member = False
    can_change_filter = True
    
    # Verificar si el usuario pertenece a un equipo
    user_membership = TeamMembership.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('organizational_unit', 'position_type').first()
    
    if user_membership:
        user_team = user_membership.organizational_unit
        is_team_member = True
        can_change_filter = False  # No pueden cambiar filtro
        
        # VALIDACIÓN DE SEGURIDAD: Si es miembro de equipo, FORZAR filtro de su equipo
        forced_equipo_filter = str(user_team.id)
        
        # Verificar si están intentando manipular el filtro
        requested_filter = request.GET.get('equipo', '')
        if requested_filter and requested_filter != forced_equipo_filter:
            # Intento de manipulación - redirigir con filtro correcto
            from django.http import HttpResponseRedirect
            from urllib.parse import urlencode
            
            # Construir URL limpia con el filtro correcto
            query_params = request.GET.copy()
            query_params['equipo'] = forced_equipo_filter
            
            return HttpResponseRedirect(f"{request.path}?{urlencode(query_params)}")
        
        # Aplicar filtro forzado
        equipo_filter = forced_equipo_filter
    else:
        # Usuario sin equipo (admin, gerentes comerciales, etc.) - acceso completo
        equipo_filter = request.GET.get('equipo', '')
        can_change_filter = True
    
    # Otros filtros
    relation_type_filter = request.GET.get('relation_type', '')
    
    # Obtener equipos para el filtro (solo si puede cambiar)
    if can_change_filter:
        equipos = OrganizationalUnit.objects.filter(is_active=True)
    else:
        # Solo mostrar su equipo en la lista
        equipos = OrganizationalUnit.objects.filter(id=user_team.id)
    
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
    if equipo_filter:
        memberships = memberships.filter(organizational_unit_id=equipo_filter)
    
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
    if equipo_filter:
        existing_relations = existing_relations.filter(
            Q(supervisor_membership__organizational_unit_id=equipo_filter) |
            Q(subordinate_membership__organizational_unit_id=equipo_filter)
        )
    
    if relation_type_filter:
        existing_relations = existing_relations.filter(relation_type=relation_type_filter)
    
    # Crear un diccionario de relaciones por subordinado para referencias rápidas
    relations_dict = {}
    for relation in existing_relations:
        subordinate_id = relation.subordinate_membership.id
        relations_dict[subordinate_id] = relation
    
    # Mostrar relaciones existentes Y miembros sin supervisor para poder asignarlos
    all_hierarchy_items = []
    processed_memberships = set()
    
    # Primero agregar todas las relaciones explícitas
    for relation in existing_relations:
        all_hierarchy_items.append(relation)
        # Marcar subordinados como procesados (ya tienen supervisor)
        processed_memberships.add(relation.subordinate_membership.id)
    
    # Luego agregar miembros que NO tienen supervisor asignado (para poder asignarlos)
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
                # Crear entrada para miembro sin supervisor (para asignación)
                unassigned_item = type('UnassignedMember', (), {
                    'id': f'unassigned_{membership.id}',
                    'supervisor_membership': None,
                    'subordinate_membership': membership,
                    'relation_type': 'UNASSIGNED',
                    'authority_level': 'NONE',
                    'is_active': membership.is_active,
                    'is_primary': False,
                    'created_at': membership.created_at,
                    'get_relation_type_display': lambda: 'Sin Supervisor',
                    'pk': f'unassigned_{membership.id}'
                })()
                all_hierarchy_items.append(unassigned_item)
    
    # Ordenar para que usuarios inactivos aparezcan primero
    def sort_key(item):
        subordinate_user = item.subordinate_membership.user
        user_priority = 0 if not subordinate_user.is_active else 1  # Inactivos primero (0 < 1)
        membership_priority = 0 if not item.subordinate_membership.is_active else 1  # Membresías inactivas primero
        time_priority = item.created_at
        return (user_priority, membership_priority, time_priority)
    
    all_hierarchy_items.sort(key=sort_key)
    
    # Aplicar filtro de tipo de relación
    if relation_type_filter:
        all_hierarchy_items = [item for item in all_hierarchy_items if item.relation_type == relation_type_filter]
    
    # Organizar por equipo
    relations_by_team = {}
    for item in all_hierarchy_items:
        if hasattr(item, 'supervisor_membership') and item.supervisor_membership:
            team_name = item.supervisor_membership.organizational_unit.name
        else:
            team_name = item.subordinate_membership.organizational_unit.name
        
        if team_name not in relations_by_team:
            relations_by_team[team_name] = []
        relations_by_team[team_name].append(item)
    
    # Paginación
    page_size = request.GET.get('page_size', '10')
    try:
        page_size = int(page_size)
        if page_size not in [10, 20, 50]:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10
    
    paginator = Paginator(all_hierarchy_items, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener estadísticas actualizadas
    total_memberships = memberships.count()
    
    stats = {
        'total_relations': len(all_hierarchy_items),
        'active_relations': len([item for item in all_hierarchy_items if item.is_active]),
        'direct_relations': existing_relations.filter(relation_type='DIRECT').count(),
        'units_with_relations': equipos.count(),
    }

    # Tipos de relaciones disponibles (incluyendo sin asignar)
    relation_types = list(HierarchyRelation.RELATION_TYPES) + [
        ('UNASSIGNED', 'Sin Supervisor')
    ]

    context = {
        'page_obj': page_obj,
        'relations_by_team': relations_by_team,
        'units': equipos,
        'equipo_filter': equipo_filter,
        'relation_type_filter': relation_type_filter,
        'relation_types': relation_types,
        'total_relations': len(all_hierarchy_items),
        'stats': stats,
        'is_team_view': False,  # Flag para indicar que es la vista plural
        'current_page_size': page_size,
        'page_size_options': [10, 20, 50],
        # Control de acceso por equipo
        'user_team': user_team,
        'is_team_member': is_team_member,
        'can_change_filter': can_change_filter,
    }
    
    return render(request, 'sales_team_management/jerarquia/list.html', context)


@login_required
@hierarchy_module_required
def jerarquia_detail(request, relation_id):
    """Ver detalle de una relación jerárquica"""
    relation = get_object_or_404(HierarchyRelation, id=relation_id)
    
    context = {
        'relation': relation,
        'supervisor_unit': relation.supervisor_membership.organizational_unit,
        'subordinate_unit': relation.subordinate_membership.organizational_unit,
    }
    
    return render(request, 'sales_team_management/jerarquia/detail.html', context)


@login_required
@hierarchy_module_required
def jerarquia_toggle(request, relation_id):
    """Activar/desactivar una relación jerárquica"""
    relation = get_object_or_404(HierarchyRelation, id=relation_id)
    
    if request.method == 'POST':
        relation.is_active = not relation.is_active
        relation.save()
        
        status = "activada" if relation.is_active else "desactivada"
        messages.success(request, f'Relación jerárquica {status} exitosamente.')
    
    return redirect('sales_team_management:jerarquia_list')


@login_required
@hierarchy_module_required
def jerarquia_equipo(request, equipo_id):
    """Jerarquía específica de un equipo"""
    
    equipo = get_object_or_404(OrganizationalUnit, id=equipo_id, is_active=True)
    
    # Obtener todas las membresías del equipo
    memberships = TeamMembership.objects.filter(
        organizational_unit=equipo,
        is_active=True
    ).select_related('user', 'position_type').order_by('position_type__hierarchy_level')
    
    # Obtener relaciones jerárquicas del equipo
    relations = HierarchyRelation.objects.filter(
        supervisor_membership__organizational_unit=equipo,
        is_active=True
    ).select_related(
        'supervisor_membership__user',
        'subordinate_membership__user',
        'supervisor_membership__position_type',
        'subordinate_membership__position_type'
    )
    
    # Construir árbol jerárquico
    hierarchy_tree = build_hierarchy_tree(memberships, relations)
    
    # Obtener supervisión directa
    direct_supervision = relations.filter(relation_type='DIRECT')
    
    context = {
        'equipo': equipo,
        'memberships': memberships,
        'relations': relations,
        'hierarchy_tree': hierarchy_tree,
        'direct_supervision': direct_supervision,
        'total_members': memberships.count(),
        'total_relations': relations.count()
    }
    
    return render(request, 'sales_team_management/jerarquia/equipo_detail.html', context)


@login_required
@hierarchy_module_required
def asignar_supervisor(request):
    """Vista específica para asignar supervisor y rol a un miembro existente"""
    
    # Obtener el miembro a asignar
    subordinate_id = request.GET.get('subordinate')
    if not subordinate_id:
        messages.error(request, 'No se especificó el miembro a asignar.')
        return redirect('sales_team_management:jerarquia_list')
    
    try:
        member = TeamMembership.objects.select_related(
            'user', 'position_type', 'organizational_unit'
        ).get(id=subordinate_id)
    except TeamMembership.DoesNotExist:
        messages.error(request, 'Miembro no encontrado.')
        return redirect('sales_team_management:jerarquia_list')
    
    # Obtener supervisores disponibles según el tipo de jerarquía
    member_level = member.position_type.hierarchy_level
    
    # Estructura rígida: solo puede ser supervisado por el nivel inmediatamente superior
    rigid_supervisors = TeamMembership.objects.filter(
        organizational_unit=member.organizational_unit,
        is_active=True,
        user__is_active=True,  # AÑADIDO: Usuario debe estar activo también
        position_type__can_supervise=True,
        position_type__hierarchy_level=member_level - 1  # Nivel inmediatamente superior
    ).exclude(
        id=member.id  # No puede supervisarse a sí mismo
    ).select_related('user', 'position_type')
    
    # Supervisión directa: puede ser supervisado por cualquier nivel superior
    direct_supervisors = TeamMembership.objects.filter(
        organizational_unit=member.organizational_unit,
        is_active=True,
        user__is_active=True,  # AÑADIDO: Usuario debe estar activo también
        position_type__can_supervise=True,
        position_type__hierarchy_level__lt=member_level  # Cualquier nivel superior
    ).exclude(
        id=member.id  # No puede supervisarse a sí mismo
    ).select_related('user', 'position_type')
    
    # Por defecto usar estructura rígida (puede cambiarse con un parámetro)
    available_supervisors = rigid_supervisors.order_by('position_type__hierarchy_level')
    
    # Obtener tipos de posición disponibles
    position_types = PositionType.objects.filter(is_active=True).order_by('hierarchy_level')
    
    if request.method == 'POST':
        # Procesar datos del formulario
        position_type_id = request.POST.get('position_type')
        direct_supervision = request.POST.get('direct_supervision') == 'on'
        supervisor_id = request.POST.get('supervisor')
        justification = request.POST.get('justification', '')
        
        # Si es supervisión directa, usar la lista de supervisores directos
        if direct_supervision:
            available_supervisors = direct_supervisors.order_by('position_type__hierarchy_level')
        
        # Valores por defecto simplificados
        assignment_type = 'PERMANENT'  # Todos permanentes por defecto
        authority_level = 'FULL'       # Autoridad completa por defecto
        relation_type = 'DIRECT' if direct_supervision else 'NORMAL'  # Según el tipo seleccionado
        is_primary = True              # Siempre supervisor principal
        
        try:
            # Validaciones
            if not position_type_id:
                messages.error(request, 'Debe seleccionar un rol/posición.')
                return render(request, 'sales_team_management/jerarquia/assign.html', {
                    'member': member,
                    'available_supervisors': available_supervisors,
                    'rigid_supervisors': rigid_supervisors,
                    'direct_supervisors': direct_supervisors,
                    'position_types': position_types
                })
            
            # Obtener la posición seleccionada para verificar el nivel
            position_type = PositionType.objects.get(id=position_type_id)
            is_manager = position_type.hierarchy_level == 1  # Gerentes son nivel 1
            
            # Solo validar supervisor si NO es gerente
            if not is_manager and not supervisor_id:
                supervision_text = 'supervisión directa' if direct_supervision else 'estructura jerárquica'
                messages.error(request, f'Debe seleccionar un supervisor para {supervision_text}.')
                return render(request, 'sales_team_management/jerarquia/assign.html', {
                    'member': member,
                    'available_supervisors': available_supervisors,
                    'rigid_supervisors': rigid_supervisors,
                    'direct_supervisors': direct_supervisors,
                    'position_types': position_types
                })
            
            # Actualizar el rol/posición del miembro
            member.position_type = position_type
            member.assignment_type = assignment_type
            member.notes = justification
            
            # ASIGNACIÓN AUTOMÁTICA DE ROL - Asignar el rol correcto según la posición
            from apps.accounts.models import Role
            try:
                # Mapear nivel jerárquico a rol
                role_name = None
                if position_type.hierarchy_level == 1:  # Gerente
                    role_name = 'Gerente de Equipo'
                elif position_type.hierarchy_level == 2:  # Jefe de Venta
                    role_name = 'Jefe de Venta'
                elif position_type.hierarchy_level == 3:  # Team Leader
                    role_name = 'Team Leader'
                elif position_type.hierarchy_level == 4:  # Vendedor
                    role_name = 'Ventas'
                
                if role_name:
                    role = Role.objects.get(name=role_name)
                    if member.user.role != role:
                        member.user.role = role
                        # Guardar inmediatamente el cambio de rol
                        member.user.save()
                        messages.info(request, f'Rol "{role_name}" asignado automáticamente a {member.user.get_full_name()}.')
            except Role.DoesNotExist:
                messages.warning(request, f'Rol "{role_name}" no encontrado en el sistema.')
            except Exception as e:
                messages.warning(request, f'Error asignando rol automáticamente: {str(e)}')
            
            # ACTIVACIÓN COMPLETA - Asegurar que CUALQUIER usuario asignado quede completamente activo
            user_was_inactive = not member.user.is_active
            membership_was_inactive = not member.is_active or member.status != 'ACTIVE'
            
            # 1. Activar el usuario a nivel de sistema
            if not member.user.is_active:
                member.user.is_active = True
                member.user.save()
                
            # 2. Activar la membresía del equipo completamente
            member.is_active = True
            member.status = 'ACTIVE'  # IMPORTANTE: Status debe ser ACTIVE también
            member.save()
            
            # Mensajes informativos
            activation_messages = []
            if user_was_inactive:
                activation_messages.append(f'Usuario {member.user.get_full_name()} activado a nivel de sistema')
            if membership_was_inactive:
                activation_messages.append(f'Membresía de equipo activada completamente')
                
            if activation_messages:
                messages.info(request, ' | '.join(activation_messages))
            
            # Solo crear relación jerárquica si hay supervisor (no para Gerentes)
            if not is_manager and supervisor_id:
                try:
                    supervisor_membership = TeamMembership.objects.get(id=supervisor_id)
                    
                    # REACTIVAR COMPLETAMENTE supervisor si está suspendido
                    supervisor_needs_reactivation = (
                        not supervisor_membership.is_active or 
                        supervisor_membership.status != 'ACTIVE' or 
                        not supervisor_membership.user.is_active
                    )
                    
                    if supervisor_needs_reactivation:
                        # Activar usuario a nivel sistema
                        if not supervisor_membership.user.is_active:
                            supervisor_membership.user.is_active = True
                            supervisor_membership.user.save()
                            
                        # Activar membresía completamente
                        supervisor_membership.is_active = True
                        supervisor_membership.status = 'ACTIVE'
                        supervisor_membership.save()
                        
                        messages.info(request, f'Supervisor {supervisor_membership.user.get_full_name()} reactivado completamente (usuario + membresía).')
                    
                    # Verificar que no existe ya una relación activa
                    existing_relation = HierarchyRelation.objects.filter(
                        subordinate_membership=member,
                        is_active=True
                    ).first()
                    
                    if existing_relation:
                        # Actualizar relación existente
                        existing_relation.supervisor_membership = supervisor_membership
                        existing_relation.relation_type = relation_type
                        existing_relation.authority_level = authority_level
                        existing_relation.is_primary = is_primary
                        existing_relation.justification = justification
                        existing_relation.save()
                        
                        messages.success(request, f'Supervisor actualizado para {member.user.get_full_name()}.')
                    else:
                        # Crear nueva relación jerárquica
                        HierarchyRelation.objects.create(
                            supervisor_membership=supervisor_membership,
                            subordinate_membership=member,
                            relation_type=relation_type,
                            authority_level=authority_level,
                            justification=justification,
                            is_primary=is_primary,
                            is_active=True
                        )
                        
                        messages.success(request, f'Supervisor asignado exitosamente a {member.user.get_full_name()}.')
                        
                except TeamMembership.DoesNotExist:
                    messages.error(request, 'Supervisor seleccionado no válido.')
                    return render(request, 'sales_team_management/jerarquia/assign.html', {
                        'member': member,
                        'available_supervisors': available_supervisors,
                        'rigid_supervisors': rigid_supervisors,
                        'direct_supervisors': direct_supervisors,
                        'position_types': position_types
                    })
            else:
                if is_manager:
                    messages.success(request, f'{member.user.get_full_name()} asignado como Gerente (no requiere supervisor).')
                else:
                    messages.success(request, f'Rol actualizado exitosamente para {member.user.get_full_name()}.')
            
            # Redirect de vuelta a la lista de jerarquía
            return redirect('sales_team_management:jerarquia_list')
            
        except PositionType.DoesNotExist:
            messages.error(request, 'Tipo de posición no válido.')
        except Exception as e:
            messages.error(request, f'Error al asignar: {str(e)}')
    
    context = {
        'member': member,
        'available_supervisors': available_supervisors,
        'rigid_supervisors': rigid_supervisors,
        'direct_supervisors': direct_supervisors,
        'position_types': position_types,
        'title': f'Asignar Supervisor y Rol - {member.user.get_full_name()}'
    }
    
    return render(request, 'sales_team_management/jerarquia/assign.html', context)


@login_required
@hierarchy_module_required
def crear_relacion_jerarquica(request):
    """Agregar miembro al equipo (nueva funcionalidad)"""
    
    equipos = OrganizationalUnit.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        # Manejar la creación de membresía de equipo
        user_id = request.POST.get('user_id')
        team_id = request.POST.get('team_id')
        position_type_id = request.POST.get('position_type')
        assignment_type = request.POST.get('assignment_type', 'PERMANENT')
        direct_supervision = request.POST.get('direct_supervision') == 'on'
        supervisor_id = request.POST.get('supervisor_id')
        notes = request.POST.get('notes', '')
        
        if user_id and team_id and position_type_id:
            try:
                from apps.accounts.models import User
                user = User.objects.get(id=user_id)
                team = OrganizationalUnit.objects.get(id=team_id, is_active=True)
                position_type = PositionType.objects.get(id=position_type_id)
                
                # Verificar si ya existe una membresía activa
                existing_membership = TeamMembership.objects.filter(
                    user=user,
                    organizational_unit=team,
                    is_active=True
                ).exists()
                
                if existing_membership:
                    return JsonResponse({
                        'success': False,
                        'error': f'{user.get_full_name()} ya es miembro activo de {team.name}'
                    })
                
                # Activar automáticamente el usuario si se le asigna un rol de supervisión o management
                if not user.is_active and (position_type.can_supervise or position_type.hierarchy_level <= 2):
                    user.is_active = True
                    user.save()
                
                # Crear la membresía
                membership = TeamMembership.objects.create(
                    user=user,
                    organizational_unit=team,
                    position_type=position_type,
                    assignment_type=assignment_type,
                    notes=notes,
                    is_active=True,
                    status='ACTIVE'
                )
                
                # Si tiene supervisión directa, crear relación jerárquica
                if direct_supervision and supervisor_id:
                    try:
                        supervisor_membership = TeamMembership.objects.get(id=supervisor_id)
                        HierarchyRelation.objects.create(
                            supervisor_membership=supervisor_membership,
                            subordinate_membership=membership,
                            relation_type='DIRECT',
                            authority_level='HIGH',
                            justification=f'Supervisión directa asignada durante la creación del miembro',
                            is_primary=True,
                            is_active=True
                        )
                    except TeamMembership.DoesNotExist:
                        pass  # No crear relación si no se encuentra el supervisor
                
                return JsonResponse({
                    'success': True,
                    'message': f'{user.get_full_name()} agregado exitosamente a {team.name}'
                })
                
            except (User.DoesNotExist, OrganizationalUnit.DoesNotExist, PositionType.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Error: Datos no válidos'
                })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Faltan datos requeridos'
            })
    
    # Obtener todas las membresías activas de todos los equipos
    memberships = TeamMembership.objects.filter(
        is_active=True
    ).select_related('user', 'position_type', 'organizational_unit').order_by(
        'organizational_unit__name', 'position_type__hierarchy_level'
    )
    
    context = {
        'equipos': equipos,
        'memberships': memberships,
        'relation_types': HierarchyRelation.RELATION_TYPES,
        'authority_levels': HierarchyRelation.AUTHORITY_LEVELS,
        'title': 'Crear Relación Jerárquica Organizacional'
    }
    
    return render(request, 'sales_team_management/jerarquia/create.html', context)


@login_required
@hierarchy_module_required
def crear_relacion_jerarquica_equipo(request, equipo_id):
    """Crear nueva relación jerárquica dentro de un equipo específico"""
    
    equipo = get_object_or_404(OrganizationalUnit, id=equipo_id, is_active=True)
    
    if request.method == 'POST':
        supervisor_id = request.POST.get('supervisor_membership')
        subordinate_id = request.POST.get('subordinate_membership')
        relation_type = request.POST.get('relation_type', 'NORMAL')
        authority_level = request.POST.get('authority_level', 'MEDIUM')
        justification = request.POST.get('justification', '')
        is_primary = request.POST.get('is_primary') == 'on'
        
        if supervisor_id and subordinate_id:
            try:
                supervisor_membership = TeamMembership.objects.get(id=supervisor_id, organizational_unit=equipo)
                subordinate_membership = TeamMembership.objects.get(id=subordinate_id, organizational_unit=equipo)
                
                # Validar que no existe ya una relación
                existing = HierarchyRelation.objects.filter(
                    supervisor_membership=supervisor_membership,
                    subordinate_membership=subordinate_membership,
                    is_active=True
                ).exists()
                
                if existing:
                    messages.error(request, 'Ya existe una relación jerárquica entre estos usuarios.')
                else:
                    # Crear la relación
                    HierarchyRelation.objects.create(
                        supervisor_membership=supervisor_membership,
                        subordinate_membership=subordinate_membership,
                        relation_type=relation_type,
                        authority_level=authority_level,
                        justification=justification,
                        is_primary=is_primary,
                        is_active=True
                    )
                    
                    messages.success(request, 'Relación jerárquica creada exitosamente.')
                    return redirect('sales_team_management:jerarquia_equipo', equipo_id=equipo.id)
                    
            except TeamMembership.DoesNotExist:
                messages.error(request, 'Error: Membresía no encontrada en este equipo.')
        else:
            messages.error(request, 'Debe seleccionar supervisor y subordinado.')
    
    # Obtener membresías del equipo específico
    memberships = TeamMembership.objects.filter(
        organizational_unit=equipo,
        is_active=True
    ).select_related('user', 'position_type')
    
    context = {
        'equipo': equipo,
        'memberships': memberships,
        'relation_types': HierarchyRelation.RELATION_TYPES,
        'authority_levels': HierarchyRelation.AUTHORITY_LEVELS,
        'title': f'Crear Relación Jerárquica - {equipo.name}'
    }
    
    return render(request, 'sales_team_management/jerarquia/create.html', context)


@login_required
@hierarchy_module_required
def editar_relacion_jerarquica(request, relation_id):
    """Editar relación jerárquica existente"""
    
    relation = get_object_or_404(HierarchyRelation, id=relation_id)
    equipo = relation.supervisor_membership.organizational_unit
    
    if request.method == 'POST':
        form = HierarchyRelationForm(request.POST, instance=relation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Relación jerárquica actualizada exitosamente.')
            return redirect('sales_team_management:jerarquia_equipo', equipo_id=equipo.id)
    else:
        form = HierarchyRelationForm(instance=relation)
    
    context = {
        'form': form,
        'relation': relation,
        'equipo': equipo,
        'title': 'Editar Relación Jerárquica'
    }
    
    return render(request, 'sales_team_management/jerarquia/edit.html', context)


@login_required
@hierarchy_module_required
def eliminar_relacion_jerarquica(request, relation_id):
    """Eliminar relación jerárquica"""
    
    relation = get_object_or_404(HierarchyRelation, id=relation_id)
    equipo = relation.supervisor_membership.organizational_unit
    
    if request.method == 'POST':
        # Desactivar en lugar de eliminar para mantener historial
        relation.is_active = False
        relation.save()
        
        messages.success(request, 'Relación jerárquica eliminada exitosamente.')
        return redirect('sales_team_management:jerarquia_equipo', equipo_id=equipo.id)
    
    context = {
        'relation': relation,
        'equipo': equipo
    }
    
    return render(request, 'sales_team_management/jerarquia/confirm_delete.html', context)


# ============================================================
# VISTAS DE ANÁLISIS DE JERARQUÍA
# ============================================================

@login_required
@hierarchy_module_required
def analisis_jerarquia(request):
    """Análisis general de la estructura jerárquica"""
    
    # Estadísticas generales
    total_units = OrganizationalUnit.objects.filter(is_active=True).count()
    total_memberships = TeamMembership.objects.filter(is_active=True).count()
    total_relations = HierarchyRelation.objects.filter(is_active=True).count()
    
    # Estadísticas por tipo de relación
    relation_stats = HierarchyRelation.objects.filter(is_active=True).values(
        'relation_type'
    ).annotate(count=Count('id'))
    
    # Estadísticas por tipo de posición
    position_stats = TeamMembership.objects.filter(is_active=True).values(
        'position_type__name'
    ).annotate(count=Count('id')).order_by('-count')
    
    # Usuarios con más supervisión directa
    top_supervisors = HierarchyRelation.objects.filter(
        is_active=True,
        relation_type='DIRECT'
    ).values(
        'supervisor_membership__user__username',
        'supervisor_membership__user__first_name',
        'supervisor_membership__user__last_name'
    ).annotate(
        subordinates_count=Count('subordinate_membership')
    ).order_by('-subordinates_count')[:10]
    
    # Detectar posibles inconsistencias
    inconsistencies = detect_hierarchy_inconsistencies()
    
    context = {
        'total_units': total_units,
        'total_memberships': total_memberships,
        'total_relations': total_relations,
        'relation_stats': relation_stats,
        'position_stats': position_stats,
        'top_supervisors': top_supervisors,
        'inconsistencies': inconsistencies
    }
    
    return render(request, 'sales_team_management/jerarquia/analisis.html', context)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def build_hierarchy_tree(memberships, relations):
    """Construye un árbol jerárquico a partir de membresías y relaciones"""
    
    # Crear diccionario de relaciones
    relations_dict = {}
    for relation in relations:
        supervisor_id = relation.supervisor_membership.id
        subordinate_id = relation.subordinate_membership.id
        
        if supervisor_id not in relations_dict:
            relations_dict[supervisor_id] = []
        relations_dict[supervisor_id].append(subordinate_id)
    
    # Encontrar raíces (usuarios sin supervisor)
    all_subordinates = set()
    for subordinates in relations_dict.values():
        all_subordinates.update(subordinates)
    
    roots = []
    for membership in memberships:
        if membership.id not in all_subordinates:
            roots.append(membership)
    
    # Construir árbol recursivamente
    def build_node(membership):
        node = {
            'membership': membership,
            'children': []
        }
        
        subordinate_ids = relations_dict.get(membership.id, [])
        for subordinate_id in subordinate_ids:
            subordinate_membership = next(
                (m for m in memberships if m.id == subordinate_id), None
            )
            if subordinate_membership:
                node['children'].append(build_node(subordinate_membership))
        
        return node
    
    tree = [build_node(root) for root in roots]
    return tree


def detect_hierarchy_inconsistencies():
    """Detecta inconsistencias en la estructura jerárquica"""
    
    inconsistencies = []
    
    # Detectar relaciones circulares
    relations = HierarchyRelation.objects.filter(is_active=True)
    
    for relation in relations:
        # Buscar si existe una relación inversa
        reverse_relation = HierarchyRelation.objects.filter(
            supervisor_membership=relation.subordinate_membership,
            subordinate_membership=relation.supervisor_membership,
            is_active=True
        ).first()
        
        if reverse_relation:
            inconsistencies.append({
                'type': 'circular',
                'description': f'Relación circular entre {relation.supervisor_membership.user.username} y {relation.subordinate_membership.user.username}',
                'relation_1': relation,
                'relation_2': reverse_relation
            })
    
    # Detectar múltiples supervisores primarios
    subordinates_with_multiple_primary = HierarchyRelation.objects.filter(
        is_active=True,
        is_primary=True
    ).values('subordinate_membership').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    for item in subordinates_with_multiple_primary:
        membership = TeamMembership.objects.get(id=item['subordinate_membership'])
        inconsistencies.append({
            'type': 'multiple_primary',
            'description': f'{membership.user.username} tiene múltiples supervisores primarios',
            'membership': membership
        })
    
    return inconsistencies


# ============================================================
# VISTAS AJAX
# ============================================================

@login_required
def get_hierarchy_json(request, equipo_id):
    """API para obtener jerarquía del equipo en JSON"""
    
    equipo = get_object_or_404(OrganizationalUnit, id=equipo_id)
    
    memberships = TeamMembership.objects.filter(
        organizational_unit=equipo,
        is_active=True
    ).select_related('user', 'position_type')
    
    relations = HierarchyRelation.objects.filter(
        supervisor_membership__organizational_unit=equipo,
        is_active=True
    ).select_related(
        'supervisor_membership__user',
        'subordinate_membership__user'
    )
    
    # Construir datos para JSON
    members_data = []
    for membership in memberships:
        members_data.append({
            'id': membership.id,
            'user_id': membership.user.id,
            'user_name': membership.user.get_full_name(),
            'username': membership.user.username,
            'position': membership.position_type.name,
            'position_code': membership.position_type.code,
            'hierarchy_level': membership.position_type.hierarchy_level
        })
    
    relations_data = []
    for relation in relations:
        relations_data.append({
            'id': relation.id,
            'supervisor_id': relation.supervisor_membership.id,
            'subordinate_id': relation.subordinate_membership.id,
            'relation_type': relation.relation_type,
            'is_primary': relation.is_primary,
            'authority_level': relation.authority_level
        })
    
    return JsonResponse({
        'success': True,
        'equipo': {
            'id': equipo.id,
            'name': equipo.name,
            'unit_type': equipo.unit_type
        },
        'members': members_data,
        'relations': relations_data
    })


@login_required
def get_available_supervisors(request, membership_id):
    """API para obtener supervisores disponibles para una membresía"""
    
    membership = get_object_or_404(TeamMembership, id=membership_id)
    equipo = membership.organizational_unit
    supervision_type = request.GET.get('type', 'rigid')  # 'rigid' o 'direct'
    
    # CAMBIO PRINCIPAL: Usar la posición seleccionada si se proporciona
    selected_position_id = request.GET.get('position_id')
    if selected_position_id:
        try:
            selected_position = PositionType.objects.get(id=selected_position_id)
            member_level = selected_position.hierarchy_level
        except PositionType.DoesNotExist:
            member_level = membership.position_type.hierarchy_level
    else:
        member_level = membership.position_type.hierarchy_level
    
    # Si es Gerente (nivel 1), no necesita supervisor
    if member_level == 1:
        return JsonResponse({
            'success': True,
            'supervisors': [],
            'supervision_type': supervision_type,
            'message': 'Gerente'
        })
    
    if supervision_type == 'direct':
        # Supervisión directa: cualquier nivel superior
        # INCLUIR usuarios suspendidos que pueden ser reactivados
        potential_supervisors = TeamMembership.objects.filter(
            organizational_unit=equipo,
            user__is_active=True,  # Usuario debe estar activo
            position_type__can_supervise=True,
            position_type__hierarchy_level__lt=member_level  # Cualquier nivel superior
        ).filter(
            # Membresías activas O suspendidas (que pueden reactivarse)
            models.Q(is_active=True) | models.Q(status='SUSPENDED')
        ).exclude(
            id=membership_id  # No puede supervisarse a sí mismo
        ).select_related('user', 'position_type')
    else:
        # Estructura rígida: solo nivel inmediatamente superior
        # INCLUIR usuarios suspendidos que pueden ser reactivados
        potential_supervisors = TeamMembership.objects.filter(
            organizational_unit=equipo,
            user__is_active=True,  # Usuario debe estar activo
            position_type__can_supervise=True,
            position_type__hierarchy_level=member_level - 1  # Nivel inmediatamente superior
        ).filter(
            # Membresías activas O suspendidas (que pueden reactivarse)
            models.Q(is_active=True) | models.Q(status='SUSPENDED')
        ).exclude(
            id=membership_id  # No puede supervisarse a sí mismo
        ).select_related('user', 'position_type')
    
    supervisors_data = []
    for supervisor in potential_supervisors:
        # Indicar si el supervisor necesita reactivación
        needs_reactivation = not supervisor.is_active or supervisor.status == 'SUSPENDED'
        display_name = supervisor.user.get_full_name()
        if needs_reactivation:
            display_name += " (será reactivado)"
            
        supervisors_data.append({
            'id': supervisor.id,
            'user_name': display_name,
            'position': supervisor.position_type.name,
            'hierarchy_level': supervisor.position_type.hierarchy_level,
            'needs_reactivation': needs_reactivation
        })
    
    # DEBUG: Agregar información de depuración para entender por qué no encuentra supervisores
    debug_info = {
        'member_level': member_level,
        'required_level': member_level - 1 if member_level > 1 else 'N/A',
        'equipo_name': equipo.name,
        'all_memberships_count': TeamMembership.objects.filter(organizational_unit=equipo).count(),
        'active_memberships_count': TeamMembership.objects.filter(organizational_unit=equipo, is_active=True).count(),
        'level_1_positions': list(PositionType.objects.filter(hierarchy_level=1, is_active=True).values('id', 'name', 'can_supervise')),
        'potential_level_1_members': []
    }
    
    # Verificar todos los miembros nivel 1 en el equipo (sin filtros para debug)
    all_level_1_members = TeamMembership.objects.filter(
        organizational_unit=equipo,
        position_type__hierarchy_level=1
    ).select_related('user', 'position_type')
    
    for member in all_level_1_members:
        debug_info['potential_level_1_members'].append({
            'user_name': member.user.get_full_name(),
            'user_id': member.user.id,
            'user_active': member.user.is_active,
            'membership_active': member.is_active,
            'position_name': member.position_type.name,
            'position_can_supervise': member.position_type.can_supervise,
            'position_active': member.position_type.is_active,
            'membership_status': member.status
        })
    
    return JsonResponse({
        'success': True,
        'supervisors': supervisors_data,
        'supervision_type': supervision_type,
        'debug': debug_info
    })