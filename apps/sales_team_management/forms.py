# apps/sales_team_management/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal
import json

# NUEVO MODELO - Sin Legacy
from .models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)
from apps.real_estate_projects.models import (
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    ComisionDesarrollo, AsignacionEquipoProyecto
)

User = get_user_model()


# ============================================================
# FORMULARIOS PARA UNIDADES ORGANIZACIONALES
# ============================================================

class OrganizationalUnitForm(forms.ModelForm):
    """Formulario para crear/editar unidades organizacionales"""
    
    # Campo toggle para habilitar jerarquía
    enable_hierarchy = forms.BooleanField(
        required=False,
        initial=False,
        label='Habilitar Estructura Jerárquica',
        help_text='Activar para asignar esta unidad como subordinada de otra unidad',
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            'onclick': 'toggleParentUnit(this.checked)',
            'id': 'id_enable_hierarchy'
        })
    )

    class Meta:
        model = OrganizationalUnit
        fields = ['name', 'description', 'unit_type', 'parent_unit', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Equipo Centro Norte'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Descripción de la unidad organizacional...'
            }),
            'unit_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'parent_unit': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'name': 'Nombre de la Unidad',
            'description': 'Descripción',
            'unit_type': 'Tipo de Unidad',
            'parent_unit': 'Unidad Padre',
            'is_active': 'Unidad Activa'
        }
        help_texts = {
            'name': 'Nombre único identificatorio de la unidad organizacional',
            'description': 'Descripción opcional de la unidad y su área de trabajo',
            'unit_type': 'Tipo de unidad organizacional (ventas, cartera, etc.)',
            'parent_unit': 'Unidad organizacional padre (opcional)',
            'is_active': 'Si la unidad está activa y puede recibir asignaciones'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar unidades padre activas, excluyendo la instancia actual
        parent_queryset = OrganizationalUnit.objects.filter(is_active=True)
        if self.instance.pk:
            parent_queryset = parent_queryset.exclude(pk=self.instance.pk)
            # Si estamos editando y ya tiene parent_unit, activar el toggle
            if self.instance.parent_unit:
                self.fields['enable_hierarchy'].initial = True
        
        self.fields['parent_unit'].queryset = parent_queryset
        
        # Configurar el campo parent_unit como no requerido y oculto por defecto
        self.fields['parent_unit'].required = False
        
        # Si no hay parent_unit establecido, ocultar el campo inicialmente
        if not (self.instance.pk and self.instance.parent_unit):
            self.fields['parent_unit'].widget.attrs.update({
                'style': 'display: none;',
                'id': 'id_parent_unit'
            })

    def clean_name(self):
        """Limpiar y validar el nombre de la unidad"""
        name = self.cleaned_data.get('name')
        
        if not name:
            raise forms.ValidationError('Este campo es obligatorio.')
        
        # Limpiar espacios del principio y final
        name = name.strip()
        
        # Validar que no esté vacío después de limpiar
        if not name:
            raise forms.ValidationError('El nombre no puede estar vacío o contener solo espacios.')
        
        # Validar unicidad considerando espacios y mayúsculas/minúsculas
        queryset = OrganizationalUnit.objects.filter(name__iexact=name)
        
        # Excluir la instancia actual si estamos editando
        if hasattr(self, 'instance') and self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            existing_unit = queryset.first()
            raise forms.ValidationError(
                f'Ya existe una unidad con el nombre "{existing_unit.name}" (ID: {existing_unit.id}). '
                f'Los nombres deben ser únicos e irrepetibles.'
            )
        
        return name
    
    def clean(self):
        """Validaciones adicionales del formulario"""
        cleaned_data = super().clean()
        parent_unit = cleaned_data.get('parent_unit')
        enable_hierarchy = cleaned_data.get('enable_hierarchy', False)
        
        # Si el toggle está desactivado, remover parent_unit
        if not enable_hierarchy:
            cleaned_data['parent_unit'] = None
        
        # Validar que no se cree una referencia circular
        if parent_unit and self.instance.pk:
            if parent_unit == self.instance:
                raise forms.ValidationError({
                    'parent_unit': 'Una unidad no puede ser su propia unidad padre.'
                })
        
        return cleaned_data


class TeamMembershipForm(forms.ModelForm):
    """Formulario para crear/editar membresías de equipo"""

    class Meta:
        model = TeamMembership
        fields = ['user', 'position_type', 'assignment_type', 'notes', 'is_active']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'position_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'assignment_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Notas adicionales sobre la membresía...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'user': 'Usuario',
            'position_type': 'Tipo de Posición',
            'assignment_type': 'Tipo de Asignación',
            'notes': 'Notas',
            'is_active': 'Membresía Activa'
        }
        help_texts = {
            'user': 'Usuario que será miembro de la unidad organizacional',
            'position_type': 'Tipo de posición/rol dentro de la unidad',
            'assignment_type': 'Tipo de asignación (permanente, temporal, etc.)',
            'notes': 'Información adicional sobre esta membresía'
        }

    def __init__(self, *args, **kwargs):
        self.organizational_unit = kwargs.pop('organizational_unit', None)
        super().__init__(*args, **kwargs)
        
        if self.organizational_unit:
            # Filtrar posiciones aplicables al tipo de unidad
            applicable_positions = PositionType.objects.filter(
                Q(applicable_unit_types__contains=self.organizational_unit.unit_type) |
                Q(applicable_unit_types='ALL'),
                is_active=True
            ).order_by('hierarchy_level')
            self.fields['position_type'].queryset = applicable_positions
            
            # Excluir usuarios que ya tienen membresía activa en esta unidad
            existing_users = TeamMembership.objects.filter(
                organizational_unit=self.organizational_unit,
                is_active=True
            ).values_list('user_id', flat=True)
            
            # Si estamos editando, incluir el usuario actual
            if self.instance.pk:
                existing_users = existing_users.exclude(id=self.instance.id)
            
            self.fields['user'].queryset = User.objects.filter(
                is_active=True
            ).exclude(id__in=existing_users)

    def clean(self):
        """Validaciones adicionales del formulario"""
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        position_type = cleaned_data.get('position_type')
        
        if user and position_type and self.organizational_unit:
            # Validar que el usuario no tenga ya una membresía activa en esta unidad
            existing_membership = TeamMembership.objects.filter(
                organizational_unit=self.organizational_unit,
                user=user,
                is_active=True
            )
            
            # Excluir la instancia actual si estamos editando
            if self.instance.pk:
                existing_membership = existing_membership.exclude(pk=self.instance.pk)
            
            if existing_membership.exists():
                raise forms.ValidationError({
                    'user': f'{user.get_full_name() or user.username} ya tiene una membresía activa en esta unidad.'
                })
        
        return cleaned_data


# ============================================================
# FORMULARIOS PARA JERARQUÍA Y RELACIONES
# ============================================================

class HierarchyRelationForm(forms.ModelForm):
    """Formulario para crear/editar relaciones jerárquicas"""

    class Meta:
        model = HierarchyRelation
        fields = ['relation_type', 'authority_level', 'justification', 'is_primary', 'is_active']
        widgets = {
            'relation_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'authority_level': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'justification': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Justificación para esta relación jerárquica...'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'relation_type': 'Tipo de Relación',
            'authority_level': 'Nivel de Autoridad',
            'justification': 'Justificación',
            'is_primary': 'Relación Primaria',
            'is_active': 'Relación Activa'
        }
        help_texts = {
            'relation_type': 'Tipo de relación jerárquica (normal, directa, funcional)',
            'authority_level': 'Nivel de autoridad en la relación',
            'justification': 'Razón o justificación para esta relación especial',
            'is_primary': 'Si esta es la relación de supervisión principal',
            'is_active': 'Si la relación está actualmente activa'
        }

    def __init__(self, *args, **kwargs):
        self.organizational_unit = kwargs.pop('organizational_unit', None)
        super().__init__(*args, **kwargs)
        
        if self.organizational_unit:
            # Obtener membresías disponibles para supervisor y subordinado
            memberships = TeamMembership.objects.filter(
                organizational_unit=self.organizational_unit,
                is_active=True
            ).select_related('user', 'position_type')
            
            # Crear campos dinámicos para supervisor y subordinado
            self.fields['supervisor_membership'] = forms.ModelChoiceField(
                queryset=memberships.filter(position_type__can_supervise=True),
                empty_label="Seleccionar supervisor",
                widget=forms.Select(attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
                }),
                label="Supervisor",
                help_text="Miembro que ejercerá la supervisión"
            )
            
            self.fields['subordinate_membership'] = forms.ModelChoiceField(
                queryset=memberships,
                empty_label="Seleccionar subordinado",
                widget=forms.Select(attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
                }),
                label="Subordinado",
                help_text="Miembro que será supervisado"
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
            
            # Validar que no exista ya una relación activa del mismo tipo
            existing_relation = HierarchyRelation.objects.filter(
                supervisor_membership=supervisor,
                subordinate_membership=subordinate,
                relation_type=cleaned_data.get('relation_type'),
                is_active=True
            ).first()
            
            if existing_relation and (not self.instance.pk or existing_relation.pk != self.instance.pk):
                raise forms.ValidationError(
                    f"Ya existe una relación activa de este tipo entre {supervisor.user.get_full_name()} y {subordinate.user.get_full_name()}."
                )
        
        return cleaned_data


# ============================================================
# FORMULARIOS PARA ESTRUCTURA DE COMISIONES
# ============================================================

class CommissionStructureForm(forms.ModelForm):
    """Formulario para crear/editar estructuras de comisiones"""

    class Meta:
        model = CommissionStructure
        fields = ['structure_name', 'commission_type', 'is_active']
        widgets = {
            'structure_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Comisiones Equipo Ventas Norte'
            }),
            'commission_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'structure_name': 'Nombre de la Estructura',
            'commission_type': 'Tipo de Comisión',
            'is_active': 'Estructura Activa'
        }
        help_texts = {
            'structure_name': 'Nombre descriptivo de la estructura de comisiones',
            'commission_type': 'Tipo de comisión (ventas, desarrollo, cartera, etc.)',
            'is_active': 'Si la estructura está activa y en uso'
        }

    def __init__(self, *args, **kwargs):
        self.organizational_unit = kwargs.pop('organizational_unit', None)
        super().__init__(*args, **kwargs)
        
        if self.organizational_unit:
            # Obtener posiciones aplicables a esta unidad
            applicable_positions = PositionType.objects.filter(
                Q(applicable_unit_types__contains=self.organizational_unit.unit_type) |
                Q(applicable_unit_types='ALL'),
                is_active=True
            ).order_by('hierarchy_level')
            
            # Configurar campos dinámicos para porcentajes por posición
            initial_percentages = {}
            if self.instance.pk and self.instance.position_percentages:
                initial_percentages = self.instance.position_percentages
            else:
                # Valores por defecto distribuidos equitativamente
                total_positions = applicable_positions.count()
                default_percentage = 100.0 / total_positions if total_positions > 0 else 0.0
                for position in applicable_positions:
                    initial_percentages[position.code] = default_percentage
            
            # Campo oculto para almacenar los porcentajes JSON
            self.fields['position_percentages'] = forms.CharField(
                widget=forms.HiddenInput(),
                initial=json.dumps(initial_percentages),
                required=False
            )
            
            # Agregar campos dinámicos para cada posición
            for position in applicable_positions:
                field_name = f'percentage_{position.code}'
                self.fields[field_name] = forms.DecimalField(
                    label=f'% {position.name}',
                    max_digits=5,
                    decimal_places=2,
                    min_value=0,
                    max_value=100,
                    initial=initial_percentages.get(position.code, 0.0),
                    widget=forms.NumberInput(attrs={
                        'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                        'step': '0.01'
                    }),
                    help_text=f'Porcentaje de comisión para la posición {position.name}'
                )

    def clean(self):
        cleaned_data = super().clean()
        
        # Recopilar porcentajes y validar que sumen 100%
        total_percentage = 0
        position_percentages = {}
        
        for field_name, value in cleaned_data.items():
            if field_name.startswith('percentage_') and value is not None:
                position_code = field_name.replace('percentage_', '')
                position_percentages[position_code] = float(value)
                total_percentage += float(value)
        
        # Permitir pequeñas diferencias de redondeo
        if abs(total_percentage - 100.0) > 0.01:
            raise forms.ValidationError(
                f'La suma de porcentajes debe ser 100%. Actual: {total_percentage:.2f}%'
            )
        
        # Guardar los porcentajes en el campo JSON
        cleaned_data['position_percentages'] = position_percentages
        
        return cleaned_data


# ============================================================
# FORMULARIOS PARA PROYECTOS (MANTENER FUNCIONALIDAD ORIGINAL)
# ============================================================

class ProyectoForm(forms.ModelForm):
    """Formulario para crear/editar proyectos"""

    # Campos personalizados para mejor UX
    gerente_proyecto = forms.ModelChoiceField(
        queryset=GerenteProyecto.objects.filter(activo=True),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label="Gerente del Proyecto",
        help_text="Gerente responsable del proyecto"
    )

    jefe_proyecto = forms.ModelChoiceField(
        queryset=JefeProyecto.objects.filter(activo=True),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label="Jefe del Proyecto",
        help_text="Jefe responsable de la ejecución del proyecto"
    )

    # ACTUALIZADO: Usar OrganizationalUnit en lugar de EquipoVenta
    equipos_venta = forms.ModelMultipleChoiceField(
        queryset=OrganizationalUnit.objects.filter(is_active=True, unit_type='SALES'),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        required=False,
        label="Unidades de Venta Asignadas",
        help_text="Unidades organizacionales que podrán vender inmuebles de este proyecto"
    )

    class Meta:
        model = Proyecto
        fields = [
            'nombre', 'descripcion', 'estado', 'gerente_proyecto',
            'jefe_proyecto', 'equipos_venta', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Residencial Las Palmas'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Descripción detallada del proyecto...'
            }),
            'estado': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'nombre': 'Nombre del Proyecto',
            'descripcion': 'Descripción',
            'estado': 'Estado del Proyecto',
            'activo': 'Proyecto Activo'
        }
        help_texts = {
            'nombre': 'Nombre comercial del proyecto',
            'estado': 'Estado actual del desarrollo del proyecto'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si estamos editando, cargar las unidades actuales
        if self.instance.pk:
            # Adaptar para el nuevo modelo - esto necesitará ajustes según el modelo real
            self.fields['equipos_venta'].initial = OrganizationalUnit.objects.filter(
                unit_type='SALES',
                is_active=True
                # Aquí necesitarás ajustar según cómo se relacionen los proyectos con las unidades
            )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        proyecto = super().save(commit=commit)

        if commit:
            # Gestionar asignaciones de unidades organizacionales
            # Esta lógica necesitará ser adaptada según el modelo real
            equipos_seleccionados = self.cleaned_data.get('equipos_venta', [])
            
            # Aquí necesitarás implementar la lógica de asignación
            # según cómo se relacionen los proyectos con las unidades organizacionales

        return proyecto


class InmuebleForm(forms.ModelForm):
    """Formulario para crear/editar inmuebles"""

    class Meta:
        model = Inmueble
        fields = [
            'codigo', 'tipo', 'm2',
            'factor_precio', 'precio_manual', 'estado',
            'caracteristicas', 'disponible_comercializacion'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: A-101'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'm2': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01'
            }),
            'factor_precio': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.0001',
                'min': '0.0001'
            }),
            'precio_manual': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01'
            }),
            'estado': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'caracteristicas': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Características especiales del inmueble...'
            })
        }


# ============================================================
# FORMULARIOS PARA COMISIONES (MANTENER LEGACY PARA PROYECTOS)
# ============================================================

class ComisionDesarrolloForm(forms.ModelForm):
    """Formulario para configurar comisiones de desarrollo"""

    class Meta:
        model = ComisionDesarrollo
        fields = ['porcentaje_gerente_proyecto', 'porcentaje_jefe_proyecto', 'activo']
        widgets = {
            'porcentaje_gerente_proyecto': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'porcentaje_jefe_proyecto': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'porcentaje_gerente_proyecto': 'Comisión Gerente de Proyecto (%)',
            'porcentaje_jefe_proyecto': 'Comisión Jefe de Proyecto (%)',
            'activo': 'Configuración Activa'
        }

    def clean(self):
        cleaned_data = super().clean()
        porcentaje_gerente = cleaned_data.get('porcentaje_gerente_proyecto', 0)
        porcentaje_jefe = cleaned_data.get('porcentaje_jefe_proyecto', 0)

        total = porcentaje_gerente + porcentaje_jefe
        if total > 100:
            raise ValidationError(
                f'La suma de los porcentajes ({total}%) no puede exceder 100%.'
            )

        return cleaned_data


# ============================================================
# FORMULARIOS PARA BÚSQUEDA Y FILTROS
# ============================================================

class OrganizationalUnitFilterForm(forms.Form):
    """Formulario para filtrar unidades organizacionales"""

    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Buscar por nombre...'
        }),
        label='Nombre'
    )

    unit_type = forms.ChoiceField(
        choices=[('', 'Todos')] + OrganizationalUnit.UNIT_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='Tipo de Unidad'
    )

    is_active = forms.ChoiceField(
        choices=[('', 'Todos'), ('true', 'Activos'), ('false', 'Inactivos')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='Estado'
    )


class ProyectoFilterForm(forms.Form):
    """Formulario para filtrar proyectos"""

    nombre = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Buscar por nombre...'
        }),
        label='Nombre'
    )

    estado = forms.ChoiceField(
        choices=[('', 'Todos')] + Proyecto.ESTADOS_PROYECTO,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='Estado'
    )

    gerente_proyecto = forms.ModelChoiceField(
        queryset=GerenteProyecto.objects.filter(activo=True),
        required=False,
        empty_label='Todos los gerentes',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='Gerente'
    )

    activo = forms.ChoiceField(
        choices=[('', 'Todos'), ('true', 'Activos'), ('false', 'Inactivos')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label='Estado'
    )
