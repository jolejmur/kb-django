# apps/sales_team_management/views/equipos_new.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.http import JsonResponse
from django import forms
from ..decorators_modules import team_management_module_required
import json

# NUEVO MODELO - Sin Legacy
from ..models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)
from ..forms import CommissionStructureForm
from apps.accounts.models import User
from apps.real_estate_projects.models import (
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    AsignacionEquipoProyecto, ComisionDesarrollo
)

# Necesitaremos crear nuevos forms
from django import forms


# ============================================================
# NUEVOS FORMS PARA EL MODELO ACTUALIZADO
# ============================================================

class OrganizationalUnitForm(forms.ModelForm):
    """Form para crear/editar unidades organizacionales"""
    class Meta:
        model = OrganizationalUnit
        fields = ['name', 'description', 'unit_type', 'parent_unit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del equipo'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'parent_unit': forms.Select(attrs={'class': 'form-control'})
        }

class TeamMembershipForm(forms.ModelForm):
    """Form para agregar miembros al equipo"""
    class Meta:
        model = TeamMembership
        fields = ['user', 'position_type', 'assignment_type', 'notes']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'position_type': forms.Select(attrs={'class': 'form-control'}),
            'assignment_type': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        }
    
    def __init__(self, *args, **kwargs):
        organizational_unit = kwargs.pop('organizational_unit', None)
        super().__init__(*args, **kwargs)
        
        if organizational_unit:
            # Filtrar posiciones aplicables al tipo de unidad
            applicable_positions = PositionType.objects.filter(
                Q(applicable_unit_types__contains=organizational_unit.unit_type) |
                Q(applicable_unit_types='ALL'),
                is_active=True
            )
            self.fields['position_type'].queryset = applicable_positions
            
            # Excluir usuarios que ya tienen membresía activa en esta unidad
            existing_users = TeamMembership.objects.filter(
                organizational_unit=organizational_unit,
                is_active=True
            ).values_list('user_id', flat=True)
            
            self.fields['user'].queryset = User.objects.filter(
                is_active=True
            ).exclude(id__in=existing_users)

# CommissionStructureForm se define en forms.py


# ============================================================
# VISTAS ACTUALIZADAS PARA NUEVO MODELO
# ============================================================

@login_required
@team_management_module_required
def equipos_list(request):
    """Lista de equipos usando el nuevo modelo"""
    
    # Filtros
    search_query = request.GET.get('search', '')
    unit_type_filter = request.GET.get('unit_type', '')
    
    # Queryset base
    equipos = OrganizationalUnit.objects.filter(is_active=True)
    
    # Aplicar filtros
    if search_query:
        equipos = equipos.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(code__icontains=search_query)
        )
    
    if unit_type_filter:
        equipos = equipos.filter(unit_type=unit_type_filter)
    
    # Agregar estadísticas
    equipos = equipos.annotate(
        total_members=Count('teammembership', filter=Q(teammembership__is_active=True)),
        managers_count=Count(
            'teammembership', 
            filter=Q(
                teammembership__is_active=True,
                teammembership__position_type__code='MANAGER'
            )
        ),
        agents_count=Count(
            'teammembership',
            filter=Q(
                teammembership__is_active=True, 
                teammembership__position_type__code='AGENT'
            )
        )
    ).order_by('unit_type', 'name')
    
    # Paginación
    paginator = Paginator(equipos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opciones para filtros
    unit_types = OrganizationalUnit.UNIT_TYPES
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'unit_type_filter': unit_type_filter,
        'unit_types': unit_types,
        'total_equipos': equipos.count()
    }
    
    return render(request, 'sales_team_management/equipos/list.html', context)


@login_required
@team_management_module_required
def equipo_detail(request, equipo_id):
    """Detalle de un equipo usando el nuevo modelo"""
    
    equipo = get_object_or_404(OrganizationalUnit, id=equipo_id, is_active=True)
    
    # Obtener TODAS las membresías activas del equipo
    all_memberships = TeamMembership.objects.filter(
        organizational_unit=equipo,
        is_active=True
    ).select_related(
        'user', 'position_type'
    ).order_by('position_type__hierarchy_level', 'user__first_name')
    
    # Paginación para todos los miembros
    from django.core.paginator import Paginator
    paginator = Paginator(all_memberships, 10)  # 10 por página
    page_number = request.GET.get('page')
    memberships = paginator.get_page(page_number)
    
    # Agrupar por tipo de posición para las estadísticas del dashboard
    members_by_position = {}
    for membership in all_memberships:  # Usar todas las membresías, no solo la página actual
        position_name = membership.position_type.name
        if position_name not in members_by_position:
            members_by_position[position_name] = []
        members_by_position[position_name].append(membership)
    
    # Obtener relaciones jerárquicas del equipo
    hierarchy_relations = HierarchyRelation.objects.filter(
        supervisor_membership__organizational_unit=equipo,
        is_active=True
    ).select_related(
        'supervisor_membership__user',
        'subordinate_membership__user'
    )
    
    # Obtener estructura de comisiones
    commission_structure = CommissionStructure.objects.filter(
        organizational_unit=equipo,
        is_active=True
    ).first()
    
    # Obtener tipos de posición para mostrar nombres en lugar de códigos
    position_types = {}
    if commission_structure and commission_structure.position_percentages:
        for position_code in commission_structure.position_percentages.keys():
            try:
                position = PositionType.objects.get(code=position_code)
                position_types[position_code] = position
            except PositionType.DoesNotExist:
                position_types[position_code] = None
    
    context = {
        'equipo': equipo,
        'unit': equipo,  # Para compatibilidad con el template
        'memberships': memberships,  # Página actual de membresías
        'members_by_position': members_by_position,
        'hierarchy_relations': hierarchy_relations,
        'commission_structure': commission_structure,
        'position_types': position_types,
        'total_members': all_memberships.count(),  # Total de todos los miembros
        'page_obj': memberships,  # Para paginación en template
    }
    
    return render(request, 'sales_team_management/equipos/detail.html', context)


@login_required
@team_management_module_required
def crear_equipo(request):
    """Crear nuevo equipo"""
    
    if request.method == 'POST':
        form = OrganizationalUnitForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            
            # Crear estructura de comisiones por defecto
            default_percentages = {
                'MANAGER': 10.0,
                'SUPERVISOR': 15.0,
                'TEAM_LEAD': 20.0,
                'AGENT': 55.0
            }
            
            CommissionStructure.objects.create(
                organizational_unit=equipo,
                structure_name=f'Comisiones {equipo.name}',
                commission_type='SALES',
                position_percentages=default_percentages
            )
            
            messages.success(request, f'Equipo "{equipo.name}" creado exitosamente.')
            return redirect('sales_team_management:equipo_detail', equipo_id=equipo.id)
    else:
        form = OrganizationalUnitForm()
    
    context = {
        'form': form,
        'title': 'Crear Nuevo Equipo'
    }
    
    return render(request, 'sales_team_management/equipos/form.html', context)


@login_required
@team_management_module_required
def agregar_miembro(request, equipo_id):
    """Agregar miembro al equipo"""
    
    equipo = get_object_or_404(OrganizationalUnit, id=equipo_id, is_active=True)
    
    if request.method == 'POST':
        # Soporte para requests AJAX (desde jerarquia/create)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'user_id' in request.POST:
            user_id = request.POST.get('user_id')
            position_type_id = request.POST.get('position_type')
            assignment_type = request.POST.get('assignment_type', 'PERMANENT')
            notes = request.POST.get('notes', '')
            
            if user_id and position_type_id:
                try:
                    from apps.accounts.models import User
                    user = User.objects.get(id=user_id)
                    position_type = PositionType.objects.get(id=position_type_id)
                    
                    # Verificar si ya existe una membresía activa
                    existing_membership = TeamMembership.objects.filter(
                        user=user,
                        organizational_unit=equipo,
                        is_active=True
                    ).exists()
                    
                    if existing_membership:
                        return JsonResponse({
                            'success': False,
                            'error': f'{user.get_full_name()} ya es miembro activo de {equipo.name}'
                        })
                    
                    # Crear la membresía
                    membership = TeamMembership.objects.create(
                        user=user,
                        organizational_unit=equipo,
                        position_type=position_type,
                        assignment_type=assignment_type,
                        notes=notes,
                        is_active=True,
                        status='ACTIVE'
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'{user.get_full_name()} agregado exitosamente a {equipo.name}'
                    })
                    
                except (User.DoesNotExist, PositionType.DoesNotExist):
                    return JsonResponse({
                        'success': False,
                        'error': 'Error: Usuario o posición no válidos'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Faltan datos requeridos'
                })
        
        # Request regular con formulario
        form = TeamMembershipForm(request.POST, organizational_unit=equipo)
        if form.is_valid():
            membership = form.save(commit=False)
            membership.organizational_unit = equipo
            membership.save()
            
            messages.success(
                request, 
                f'{membership.user.get_full_name()} agregado como {membership.position_type.name} exitosamente.'
            )
            return redirect('sales_team_management:equipo_detail', equipo_id=equipo.id)
    else:
        form = TeamMembershipForm(organizational_unit=equipo)
    
    context = {
        'form': form,
        'equipo': equipo,
        'unit': equipo,  # For template compatibility
        'title': f'Agregar Miembro a {equipo.name}'
    }
    
    return render(request, 'sales_team_management/equipos/agregar_miembro.html', context)


@login_required
@team_management_module_required
def editar_miembro(request, membership_id):
    """Editar membresía de equipo"""
    
    membership = get_object_or_404(TeamMembership, id=membership_id)
    equipo = membership.organizational_unit
    
    if request.method == 'POST':
        form = TeamMembershipForm(
            request.POST, 
            instance=membership,
            organizational_unit=equipo
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Membresía actualizada exitosamente.')
            return redirect('sales_team_management:equipo_detail', equipo_id=equipo.id)
    else:
        form = TeamMembershipForm(instance=membership, organizational_unit=equipo)
    
    context = {
        'form': form,
        'membership': membership,
        'equipo': equipo,
        'title': f'Editar Membresía - {membership.user.get_full_name()}'
    }
    
    return render(request, 'sales_team_management/equipos/editar_miembro.html', context)


@login_required
@team_management_module_required
def remover_miembro(request, membership_id):
    """Remover miembro del equipo (desactivar)"""
    
    membership = get_object_or_404(TeamMembership, id=membership_id)
    equipo = membership.organizational_unit
    
    if request.method == 'POST':
        # Desactivar en lugar de eliminar para mantener historial
        membership.is_active = False
        membership.status = 'TERMINATED'
        membership.save()
        
        messages.success(
            request, 
            f'{membership.user.get_full_name()} removido del equipo exitosamente.'
        )
        return redirect('sales_team_management:equipo_detail', equipo_id=equipo.id)
    
    context = {
        'membership': membership,
        'equipo': equipo
    }
    
    return render(request, 'sales_team_management/equipos/confirm_remove.html', context)


# ============================================================
# VISTAS AJAX PARA INTERFAZ DINÁMICA
# ============================================================

@login_required
@team_management_module_required
def get_team_members_json(request, equipo_id):
    """API para obtener miembros del equipo en JSON"""
    
    equipo = get_object_or_404(OrganizationalUnit, id=equipo_id)
    
    memberships = TeamMembership.objects.filter(
        organizational_unit=equipo,
        is_active=True
    ).select_related('user', 'position_type')
    
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
    
    return JsonResponse({
        'success': True,
        'equipo': {
            'id': equipo.id,
            'name': equipo.name,
            'unit_type': equipo.unit_type
        },
        'members': members_data
    })


@login_required
@team_management_module_required
def get_available_positions(request, equipo_id):
    """API para obtener posiciones disponibles para un equipo"""
    
    equipo = get_object_or_404(OrganizationalUnit, id=equipo_id)
    
    positions = PositionType.objects.filter(
        Q(applicable_unit_types__contains=equipo.unit_type) |
        Q(applicable_unit_types='ALL'),
        is_active=True
    ).order_by('hierarchy_level')
    
    positions_data = []
    for position in positions:
        positions_data.append({
            'id': position.id,
            'code': position.code,
            'name': position.name,
            'hierarchy_level': position.hierarchy_level,
            'can_supervise': position.can_supervise
        })
    
    return JsonResponse({
        'success': True,
        'positions': positions_data
    })