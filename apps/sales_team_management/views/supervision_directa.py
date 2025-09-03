# apps/sales_team_management/views/supervision_directa.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django import forms

# NUEVO MODELO - Sin Legacy
from ..models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)

User = get_user_model()


# ============================================================
# FORMS PARA SUPERVISIÓN DIRECTA
# ============================================================

class DirectSupervisionForm(forms.ModelForm):
    """Form para crear/editar relaciones de supervisión directa"""
    class Meta:
        model = HierarchyRelation
        fields = ['relation_type', 'authority_level', 'justification', 'is_primary']
        widgets = {
            'relation_type': forms.Select(attrs={'class': 'form-control'}),
            'authority_level': forms.Select(attrs={'class': 'form-control'}),
            'justification': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        organizational_unit = kwargs.pop('organizational_unit', None)
        super().__init__(*args, **kwargs)
        
        if organizational_unit:
            # Filtrar solo relaciones de supervisión directa
            self.fields['relation_type'].choices = [
                ('DIRECT', 'Supervisión Directa'),
                ('FUNCTIONAL', 'Supervisión Funcional')
            ]
            
            # Obtener membresías disponibles para supervisor y subordinado
            memberships = TeamMembership.objects.filter(
                organizational_unit=organizational_unit,
                is_active=True
            ).select_related('user', 'position_type')
            
            # Crear campos dinámicos para supervisor y subordinado
            self.fields['supervisor_membership'] = forms.ModelChoiceField(
                queryset=memberships.filter(position_type__can_supervise=True),
                empty_label="Seleccionar supervisor",
                widget=forms.Select(attrs={'class': 'form-control'})
            )
            
            self.fields['subordinate_membership'] = forms.ModelChoiceField(
                queryset=memberships,
                empty_label="Seleccionar subordinado",
                widget=forms.Select(attrs={'class': 'form-control'})
            )
    
    def clean(self):
        cleaned_data = super().clean()
        supervisor = cleaned_data.get('supervisor_membership')
        subordinate = cleaned_data.get('subordinate_membership')
        
        if supervisor and subordinate:
            # Validar que no sea auto-supervisión
            if supervisor.user == subordinate.user:
                raise forms.ValidationError("Un usuario no puede supervisarse a sí mismo.")
            
            # Validar jerarquía (supervisor debe tener nivel jerárquico menor)
            if supervisor.position_type.hierarchy_level >= subordinate.position_type.hierarchy_level:
                raise forms.ValidationError(
                    f"El supervisor ({supervisor.position_type.name}) debe tener un nivel jerárquico superior al subordinado ({subordinate.position_type.name})."
                )
            
            # Validar que no exista ya una relación directa activa
            existing_relation = HierarchyRelation.objects.filter(
                supervisor_membership=supervisor,
                subordinate_membership=subordinate,
                relation_type='DIRECT',
                is_active=True
            ).first()
            
            if existing_relation and (not self.instance.pk or existing_relation.pk != self.instance.pk):
                raise forms.ValidationError(
                    f"Ya existe una relación de supervisión directa activa entre {supervisor.user.get_full_name()} y {subordinate.user.get_full_name()}."
                )
        
        return cleaned_data


# ============================================================
# VISTAS PARA SUPERVISIÓN DIRECTA USANDO NUEVO MODELO
# ============================================================

@login_required
@permission_required('sales_team_management.view_hierarchyrelation', raise_exception=True)
def supervision_directa_list(request):
    """Lista todas las relaciones de supervisión directa"""
    
    # Filtros de búsqueda
    search_query = request.GET.get('search', '')
    unit_filter = request.GET.get('unit', '')
    relation_type_filter = request.GET.get('relation_type', '')
    estado_filter = request.GET.get('estado', '')
    
    # Query base - solo relaciones de supervisión directa
    supervisiones = HierarchyRelation.objects.filter(
        relation_type__in=['DIRECT', 'FUNCTIONAL']
    ).select_related(
        'supervisor_membership__user',
        'supervisor_membership__position_type',
        'supervisor_membership__organizational_unit',
        'subordinate_membership__user',
        'subordinate_membership__position_type',
        'subordinate_membership__organizational_unit'
    ).order_by('-created_at')
    
    # Aplicar filtros
    if search_query:
        supervisiones = supervisiones.filter(
            Q(supervisor_membership__user__first_name__icontains=search_query) |
            Q(supervisor_membership__user__last_name__icontains=search_query) |
            Q(supervisor_membership__user__username__icontains=search_query) |
            Q(subordinate_membership__user__first_name__icontains=search_query) |
            Q(subordinate_membership__user__last_name__icontains=search_query) |
            Q(subordinate_membership__user__username__icontains=search_query)
        )
    
    if unit_filter:
        supervisiones = supervisiones.filter(
            Q(supervisor_membership__organizational_unit_id=unit_filter) |
            Q(subordinate_membership__organizational_unit_id=unit_filter)
        )
    
    if relation_type_filter:
        supervisiones = supervisiones.filter(relation_type=relation_type_filter)
    
    if estado_filter == 'activo':
        supervisiones = supervisiones.filter(is_active=True)
    elif estado_filter == 'inactivo':
        supervisiones = supervisiones.filter(is_active=False)
    
    # Paginación
    paginator = Paginator(supervisiones, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    units = OrganizationalUnit.objects.filter(is_active=True).order_by('name')
    relation_types = [
        ('DIRECT', 'Supervisión Directa'),
        ('FUNCTIONAL', 'Supervisión Funcional')
    ]
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'unit_filter': unit_filter,
        'relation_type_filter': relation_type_filter,
        'estado_filter': estado_filter,
        'units': units,
        'relation_types': relation_types,
        'title': 'Supervisiones Directas'
    }
    
    return render(request, 'sales_team_management/supervision_directa/list.html', context)


@login_required
@permission_required('sales_team_management.add_hierarchyrelation', raise_exception=True)
def supervision_directa_create(request):
    """Crear nueva relación de supervisión directa"""
    
    unit_id = request.GET.get('unit')
    unit = None
    if unit_id:
        unit = get_object_or_404(OrganizationalUnit, id=unit_id, is_active=True)
    
    if request.method == 'POST':
        form = DirectSupervisionForm(request.POST, organizational_unit=unit)
        supervisor_id = request.POST.get('supervisor_membership')
        subordinate_id = request.POST.get('subordinate_membership')
        
        if form.is_valid() and supervisor_id and subordinate_id:
            try:
                supervisor_membership = TeamMembership.objects.get(id=supervisor_id)
                subordinate_membership = TeamMembership.objects.get(id=subordinate_id)
                
                relation = form.save(commit=False)
                relation.supervisor_membership = supervisor_membership
                relation.subordinate_membership = subordinate_membership
                relation.save()
                
                messages.success(
                    request, 
                    f'Supervisión directa creada: {supervisor_membership.user.get_full_name()} → {subordinate_membership.user.get_full_name()}'
                )
                return redirect('sales_team_management:supervision_directa_list')
                
            except TeamMembership.DoesNotExist:
                messages.error(request, 'Error: Membresía no encontrada.')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = DirectSupervisionForm(organizational_unit=unit)
    
    context = {
        'form': form,
        'title': 'Crear Supervisión Directa',
        'action': 'Crear',
        'unit': unit
    }
    
    return render(request, 'sales_team_management/supervision_directa/form.html', context)


@login_required
@permission_required('sales_team_management.change_hierarchyrelation', raise_exception=True)
def supervision_directa_edit(request, pk):
    """Editar relación de supervisión directa"""
    
    relation = get_object_or_404(HierarchyRelation, pk=pk)
    unit = relation.supervisor_membership.organizational_unit
    
    if request.method == 'POST':
        form = DirectSupervisionForm(request.POST, instance=relation, organizational_unit=unit)
        if form.is_valid():
            relation = form.save()
            messages.success(
                request, 
                f'Supervisión directa actualizada: {relation.supervisor_membership.user.get_full_name()} → {relation.subordinate_membership.user.get_full_name()}'
            )
            return redirect('sales_team_management:supervision_directa_list')
    else:
        form = DirectSupervisionForm(instance=relation, organizational_unit=unit)
    
    context = {
        'form': form,
        'relation': relation,
        'unit': unit,
        'title': 'Editar Supervisión Directa',
        'action': 'Actualizar'
    }
    
    return render(request, 'sales_team_management/supervision_directa/form.html', context)


@login_required
@permission_required('sales_team_management.view_hierarchyrelation', raise_exception=True)
def supervision_directa_detail(request, pk):
    """Ver detalles de relación de supervisión directa"""
    
    relation = get_object_or_404(
        HierarchyRelation.objects.select_related(
            'supervisor_membership__user',
            'supervisor_membership__position_type',
            'supervisor_membership__organizational_unit',
            'subordinate_membership__user',
            'subordinate_membership__position_type',
            'subordinate_membership__organizational_unit'
        ), 
        pk=pk
    )
    
    context = {
        'relation': relation,
        'title': f'Supervisión Directa: {relation.supervisor_membership.user.get_full_name()} → {relation.subordinate_membership.user.get_full_name()}'
    }
    
    return render(request, 'sales_team_management/supervision_directa/detail.html', context)


@login_required
@permission_required('sales_team_management.change_hierarchyrelation', raise_exception=True)
@require_http_methods(["POST"])
def supervision_directa_toggle(request, pk):
    """Activar/desactivar relación de supervisión directa"""
    
    relation = get_object_or_404(HierarchyRelation, pk=pk)
    
    if relation.is_active:
        relation.is_active = False
        relation.save()
        messages.success(
            request, 
            f'Supervisión directa desactivada: {relation.supervisor_membership.user.get_full_name()} → {relation.subordinate_membership.user.get_full_name()}'
        )
    else:
        # Validar que no haya otra supervisión directa activa para el mismo subordinado
        existing_relation = HierarchyRelation.objects.filter(
            subordinate_membership=relation.subordinate_membership,
            relation_type='DIRECT',
            is_active=True
        ).exclude(pk=relation.pk).first()
        
        if existing_relation:
            messages.error(
                request, 
                f'No se puede activar: {relation.subordinate_membership.user.get_full_name()} ya tiene supervisión directa activa con {existing_relation.supervisor_membership.user.get_full_name()}'
            )
        else:
            relation.is_active = True
            relation.save()
            messages.success(
                request, 
                f'Supervisión directa activada: {relation.supervisor_membership.user.get_full_name()} → {relation.subordinate_membership.user.get_full_name()}'
            )
    
    return redirect('sales_team_management:supervision_directa_list')


@login_required
@permission_required('sales_team_management.delete_hierarchyrelation', raise_exception=True)
def supervision_directa_delete(request, pk):
    """Eliminar relación de supervisión directa"""
    
    relation = get_object_or_404(HierarchyRelation, pk=pk)
    
    if request.method == 'POST':
        supervisor_name = relation.supervisor_membership.user.get_full_name()
        subordinate_name = relation.subordinate_membership.user.get_full_name()
        relation.delete()
        
        messages.success(
            request, 
            f'Supervisión directa eliminada: {supervisor_name} → {subordinate_name}'
        )
        return redirect('sales_team_management:supervision_directa_list')
    
    context = {
        'relation': relation,
        'title': 'Confirmar Eliminación'
    }
    
    return render(request, 'sales_team_management/supervision_directa/delete.html', context)


# VISTAS AJAX USANDO NUEVO MODELO
# ============================================================

@login_required
@require_http_methods(["GET"])
def ajax_supervisores_disponibles(request):
    """AJAX: Obtiene supervisores disponibles para una unidad organizacional"""
    
    unit_id = request.GET.get('unit_id')
    if not unit_id:
        return JsonResponse({'error': 'ID de unidad requerido'}, status=400)
    
    try:
        unit = OrganizationalUnit.objects.get(id=unit_id, is_active=True)
    except OrganizationalUnit.DoesNotExist:
        return JsonResponse({'error': 'Unidad no encontrada'}, status=404)
    
    # Obtener membresías que pueden supervisar
    supervisors = TeamMembership.objects.filter(
        organizational_unit=unit,
        is_active=True,
        position_type__can_supervise=True
    ).select_related('user', 'position_type')
    
    supervisores_data = []
    for supervisor in supervisors:
        supervisores_data.append({
            'id': supervisor.id,
            'user_id': supervisor.user.id,
            'nombre': supervisor.user.get_full_name() or supervisor.user.username,
            'position': supervisor.position_type.name,
            'hierarchy_level': supervisor.position_type.hierarchy_level
        })
    
    return JsonResponse({'supervisores': supervisores_data})


@login_required
@require_http_methods(["GET"])
def ajax_subordinados_disponibles(request):
    """AJAX: Obtiene subordinados disponibles para una unidad organizacional"""
    
    unit_id = request.GET.get('unit_id')
    supervisor_membership_id = request.GET.get('supervisor_membership_id')
    
    if not unit_id:
        return JsonResponse({'error': 'ID de unidad requerido'}, status=400)
    
    try:
        unit = OrganizationalUnit.objects.get(id=unit_id, is_active=True)
    except OrganizationalUnit.DoesNotExist:
        return JsonResponse({'error': 'Unidad no encontrada'}, status=404)
    
    # Obtener todas las membresías de la unidad
    subordinates = TeamMembership.objects.filter(
        organizational_unit=unit,
        is_active=True
    ).select_related('user', 'position_type')
    
    # Si hay supervisor seleccionado, filtrar por nivel jerárquico
    if supervisor_membership_id:
        try:
            supervisor = TeamMembership.objects.get(id=supervisor_membership_id)
            # Solo mostrar subordinados con nivel jerárquico mayor (menos senior)
            subordinates = subordinates.filter(
                position_type__hierarchy_level__gt=supervisor.position_type.hierarchy_level
            ).exclude(id=supervisor.id)
        except TeamMembership.DoesNotExist:
            pass
    
    subordinados_data = []
    for subordinate in subordinates:
        subordinados_data.append({
            'id': subordinate.id,
            'user_id': subordinate.user.id,
            'nombre': subordinate.user.get_full_name() or subordinate.user.username,
            'position': subordinate.position_type.name,
            'hierarchy_level': subordinate.position_type.hierarchy_level
        })
    
    return JsonResponse({'subordinados': subordinados_data})


@login_required
@require_http_methods(["GET"])
def ajax_validar_supervision_relation(request):
    """AJAX: Valida si una relación de supervisión es válida"""
    
    supervisor_membership_id = request.GET.get('supervisor_membership_id')
    subordinate_membership_id = request.GET.get('subordinate_membership_id')
    
    if not all([supervisor_membership_id, subordinate_membership_id]):
        return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
    
    try:
        supervisor = TeamMembership.objects.get(id=supervisor_membership_id)
        subordinate = TeamMembership.objects.get(id=subordinate_membership_id)
    except TeamMembership.DoesNotExist:
        return JsonResponse({'error': 'Membresía no encontrada'}, status=404)
    
    # Validaciones
    validations = {
        'valid': True,
        'messages': []
    }
    
    # No puede supervisarse a sí mismo
    if supervisor.user == subordinate.user:
        validations['valid'] = False
        validations['messages'].append('Un usuario no puede supervisarse a sí mismo')
    
    # Supervisor debe tener nivel jerárquico menor (más senior)
    if supervisor.position_type.hierarchy_level >= subordinate.position_type.hierarchy_level:
        validations['valid'] = False
        validations['messages'].append(
            f'El supervisor ({supervisor.position_type.name}) debe tener un nivel jerárquico superior al subordinado ({subordinate.position_type.name})'
        )
    
    # No debe existir ya una relación directa activa
    existing_relation = HierarchyRelation.objects.filter(
        supervisor_membership=supervisor,
        subordinate_membership=subordinate,
        relation_type='DIRECT',
        is_active=True
    ).exists()
    
    if existing_relation:
        validations['valid'] = False
        validations['messages'].append('Ya existe una relación de supervisión directa activa entre estos usuarios')
    
    # Tipos de supervisión recomendados
    recommended_types = []
    level_diff = subordinate.position_type.hierarchy_level - supervisor.position_type.hierarchy_level
    
    if level_diff == 1:
        recommended_types.append(('NORMAL', 'Supervisión Normal (niveles consecutivos)'))
    elif level_diff > 1:
        recommended_types.append(('DIRECT', 'Supervisión Directa (saltando niveles)'))
        recommended_types.append(('FUNCTIONAL', 'Supervisión Funcional'))
    
    return JsonResponse({
        'validations': validations,
        'recommended_types': recommended_types,
        'supervisor_info': {
            'name': supervisor.user.get_full_name(),
            'position': supervisor.position_type.name,
            'level': supervisor.position_type.hierarchy_level
        },
        'subordinate_info': {
            'name': subordinate.user.get_full_name(),
            'position': subordinate.position_type.name,
            'level': subordinate.position_type.hierarchy_level
        }
    })