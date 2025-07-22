# apps/sales/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    ComisionVenta
)
from apps.real_estate_projects.models import (
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    ComisionDesarrollo, AsignacionEquipoProyecto
)

User = get_user_model()


# ============================================================
# FORMULARIOS PARA EQUIPOS DE VENTA
# ============================================================

class EquipoVentaForm(forms.ModelForm):
    """Formulario para crear/editar equipos de venta"""

    class Meta:
        model = EquipoVenta
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Equipo Centro Norte'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Descripción del equipo de ventas...'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'nombre': 'Nombre del Equipo',
            'descripcion': 'Descripción',
            'activo': 'Equipo Activo'
        }
        help_texts = {
            'nombre': 'Nombre único identificatorio del equipo de ventas (se limpiarán automáticamente los espacios)',
            'descripcion': 'Descripción opcional del equipo y su área de trabajo',
            'activo': 'Si el equipo está activo y puede recibir asignaciones'
        }

    def clean_nombre(self):
        """Limpiar y validar el nombre del equipo"""
        nombre = self.cleaned_data.get('nombre')
        
        if not nombre:
            raise forms.ValidationError('Este campo es obligatorio.')
        
        # Limpiar espacios del principio y final
        nombre = nombre.strip()
        
        # Validar que no esté vacío después de limpiar
        if not nombre:
            raise forms.ValidationError('El nombre no puede estar vacío o contener solo espacios.')
        
        # Validar unicidad considerando espacios y mayúsculas/minúsculas
        queryset = EquipoVenta.objects.filter(nombre__iexact=nombre)
        
        # Excluir la instancia actual si estamos editando
        if hasattr(self, 'instance') and self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            existing_equipo = queryset.first()
            raise forms.ValidationError(
                f'Ya existe un equipo con el nombre "{existing_equipo.nombre}" (ID: {existing_equipo.id}). '
                f'Los nombres deben ser únicos e irrepetibles.'
            )
        
        return nombre
    
    def clean(self):
        """Validaciones adicionales del formulario"""
        cleaned_data = super().clean()
        return cleaned_data


class MiembroEquipoForm(forms.Form):
    """Formulario unificado para agregar miembros del equipo con roles"""
    
    ROLES_CHOICES = [
        ('gerente', 'Gerente de Equipo'),
        ('jefe_venta', 'Jefe de Venta'),
        ('team_leader', 'Team Leader'),
        ('vendedor', 'Vendedor'),
    ]
    
    usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label="Usuario",
        help_text="Selecciona el usuario para agregar al equipo"
    )
    
    rol = forms.ChoiceField(
        choices=ROLES_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label="Rol en el Equipo",
        help_text="Selecciona el rol que tendrá en la jerarquía del equipo"
    )
    
    # Campo opcional para jefes de venta, team leaders y vendedores
    supervisor = forms.ModelChoiceField(
        queryset=User.objects.none(),  # Se llenará dinámicamente
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label="Supervisor",
        help_text="Selecciona el supervisor directo (si aplica)"
    )
    
    def __init__(self, *args, **kwargs):
        self.equipo = kwargs.pop('equipo', None)
        self.usuario_actual = kwargs.pop('usuario_actual', None)  # Usuario que se está editando
        super().__init__(*args, **kwargs)
        
        if self.equipo:
            # Filtrar usuarios que ya están en CUALQUIER equipo (un usuario solo puede pertenecer a un equipo)
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
            
            # Filtrar usuarios disponibles (solo usuarios que no están en ningún equipo)
            self.fields['usuario'].queryset = User.objects.filter(
                is_active=True
            ).exclude(id__in=usuarios_ocupados)
            
            # Poblar el campo supervisor con todos los usuarios potenciales supervisores
            # Se refinará por JavaScript en el frontend, pero Django necesita todas las opciones posibles
            supervisores_disponibles = set()
            
            # Gerentes del equipo (pueden ser supervisores de jefes de venta)
            for gerente in self.equipo.gerenteequipo_set.filter(activo=True):
                supervisores_disponibles.add(gerente.usuario.id)
            
            # Jefes de venta del equipo (pueden ser supervisores de team leaders)
            for gerente in self.equipo.gerenteequipo_set.filter(activo=True):
                for jefe in gerente.jefeventas.filter(activo=True):
                    supervisores_disponibles.add(jefe.usuario.id)
            
            # Team leaders del equipo (pueden ser supervisores de vendedores)
            for gerente in self.equipo.gerenteequipo_set.filter(activo=True):
                for jefe in gerente.jefeventas.filter(activo=True):
                    for leader in jefe.teamleaders.filter(activo=True):
                        supervisores_disponibles.add(leader.usuario.id)
            
            # Excluir el usuario actual de los supervisores disponibles
            if self.usuario_actual:
                supervisores_disponibles.discard(self.usuario_actual.id)
            
            # Establecer el queryset del supervisor con todos los posibles supervisores
            self.fields['supervisor'].queryset = User.objects.filter(
                id__in=supervisores_disponibles
            ).order_by('first_name', 'last_name', 'username')
    
    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get('rol')
        supervisor = cleaned_data.get('supervisor')
        usuario = cleaned_data.get('usuario')
        
        if not rol or not usuario:
            return cleaned_data
            
        # Validar si ya hay un gerente activo y se intenta agregar otro
        if rol == 'gerente' and self.equipo:
            gerentes_activos = self.equipo.gerenteequipo_set.filter(activo=True)
            if gerentes_activos.exists():
                gerente_actual = gerentes_activos.first()
                raise forms.ValidationError({
                    'rol': f'Este equipo ya tiene un gerente activo: {gerente_actual.usuario.get_full_name() or gerente_actual.usuario.username}. '
                           f'Solo puede haber un gerente por equipo. Para cambiar el gerente, primero desactiva el actual.'
                })
        
        # Validar que el usuario no esté ya asignado en CUALQUIER equipo (un usuario solo puede pertenecer a un equipo)
        if usuario:
            from .models import EquipoVenta
            
            # Buscar en todos los equipos si el usuario ya está asignado
            equipos_del_usuario = []
            
            # Verificar en gerentes de todos los equipos
            gerente_equipos = GerenteEquipo.objects.filter(usuario=usuario, activo=True)
            for ge in gerente_equipos:
                if ge.equipo_venta != self.equipo:  # Solo reportar si es de otro equipo
                    equipos_del_usuario.append(f'Gerente en "{ge.equipo_venta.nombre}"')
            
            # Verificar en jefes de venta de todos los equipos
            jefe_ventas = JefeVenta.objects.filter(usuario=usuario, activo=True)
            for jv in jefe_ventas:
                if jv.gerente_equipo.equipo_venta != self.equipo:  # Solo reportar si es de otro equipo
                    equipos_del_usuario.append(f'Jefe de Venta en "{jv.gerente_equipo.equipo_venta.nombre}"')
            
            # Verificar en team leaders de todos los equipos
            team_leaders = TeamLeader.objects.filter(usuario=usuario, activo=True)
            for tl in team_leaders:
                equipo_tl = tl.jefe_venta.gerente_equipo.equipo_venta
                if equipo_tl != self.equipo:  # Solo reportar si es de otro equipo
                    equipos_del_usuario.append(f'Team Leader en "{equipo_tl.nombre}"')
            
            # Verificar en vendedores de todos los equipos
            vendedores = Vendedor.objects.filter(usuario=usuario, activo=True)
            for v in vendedores:
                equipo_v = v.team_leader.jefe_venta.gerente_equipo.equipo_venta
                if equipo_v != self.equipo:  # Solo reportar si es de otro equipo
                    equipos_del_usuario.append(f'Vendedor en "{equipo_v.nombre}"')
            
            # Si el usuario ya está en otros equipos, mostrar error
            if equipos_del_usuario:
                raise forms.ValidationError({
                    'usuario': f'{usuario.get_full_name() or usuario.username} ya pertenece a otro equipo: {", ".join(equipos_del_usuario)}. '
                               f'Un usuario solo puede pertenecer a un equipo a la vez.'
                })
            
            # Verificar que no esté ya asignado en el equipo actual con otro rol
            if self.equipo:
                # Verificar en gerentes del equipo actual
                if self.equipo.gerenteequipo_set.filter(usuario=usuario, activo=True).exists():
                    raise forms.ValidationError({
                        'usuario': f'{usuario.get_full_name() or usuario.username} ya es gerente de este equipo.'
                    })
                
                # Verificar en jefes de venta del equipo actual
                for gerente in self.equipo.gerenteequipo_set.all():
                    if gerente.jefeventas.filter(usuario=usuario, activo=True).exists():
                        raise forms.ValidationError({
                            'usuario': f'{usuario.get_full_name() or usuario.username} ya es jefe de venta en este equipo.'
                        })
                    
                    # Verificar en team leaders del equipo actual
                    for jefe in gerente.jefeventas.all():
                        if jefe.teamleaders.filter(usuario=usuario, activo=True).exists():
                            raise forms.ValidationError({
                                'usuario': f'{usuario.get_full_name() or usuario.username} ya es team leader en este equipo.'
                            })
                        
                        # Verificar en vendedores del equipo actual
                        for leader in jefe.teamleaders.all():
                            if leader.vendedores.filter(usuario=usuario, activo=True).exists():
                                raise forms.ValidationError({
                                    'usuario': f'{usuario.get_full_name() or usuario.username} ya es vendedor en este equipo.'
                                })
        
        # Validar que roles que requieren supervisor lo tengan
        if rol in ['jefe_venta', 'team_leader', 'vendedor'] and not supervisor:
            if rol == 'jefe_venta':
                raise forms.ValidationError({
                    'supervisor': 'Los jefes de venta deben tener un gerente como supervisor.'
                })
            elif rol == 'team_leader':
                raise forms.ValidationError({
                    'supervisor': 'Los team leaders deben tener un jefe de venta como supervisor.'
                })
            elif rol == 'vendedor':
                raise forms.ValidationError({
                    'supervisor': 'Los vendedores deben tener un team leader como supervisor.'
                })
        
        # Validar que el supervisor sea del rol correcto
        if supervisor and rol:
            if rol == 'jefe_venta':
                # El supervisor debe ser un gerente del equipo
                if not self.equipo.gerenteequipo_set.filter(usuario=supervisor, activo=True).exists():
                    raise forms.ValidationError({
                        'supervisor': 'El supervisor seleccionado no es un gerente activo de este equipo.'
                    })
            elif rol == 'team_leader':
                # El supervisor debe ser un jefe de venta del equipo
                es_jefe_venta = False
                for gerente in self.equipo.gerenteequipo_set.filter(activo=True):
                    if gerente.jefeventas.filter(usuario=supervisor, activo=True).exists():
                        es_jefe_venta = True
                        break
                if not es_jefe_venta:
                    raise forms.ValidationError({
                        'supervisor': 'El supervisor seleccionado no es un jefe de venta activo de este equipo.'
                    })
            elif rol == 'vendedor':
                # El supervisor debe ser un team leader del equipo
                es_team_leader = False
                for gerente in self.equipo.gerenteequipo_set.filter(activo=True):
                    for jefe in gerente.jefeventas.filter(activo=True):
                        if jefe.teamleaders.filter(usuario=supervisor, activo=True).exists():
                            es_team_leader = True
                            break
                    if es_team_leader:
                        break
                if not es_team_leader:
                    raise forms.ValidationError({
                        'supervisor': 'El supervisor seleccionado no es un team leader activo de este equipo.'
                    })
        
        return cleaned_data


class GerenteEquipoForm(forms.ModelForm):
    """Formulario para asignar gerentes a equipos"""

    usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label="Usuario",
        help_text="Selecciona el usuario que será gerente de este equipo"
    )

    class Meta:
        model = GerenteEquipo
        fields = ['usuario', 'equipo_venta', 'activo']
        widgets = {
            'equipo_venta': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'equipo_venta': 'Equipo de Venta',
            'activo': 'Asignación Activa'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar equipos activos
        self.fields['equipo_venta'].queryset = EquipoVenta.objects.filter(activo=True)

        # Si estamos editando, excluir el usuario actual para evitar duplicados
        if self.instance.pk:
            self.fields['usuario'].queryset = User.objects.filter(
                is_active=True
            ).exclude(
                gerente_equipos__equipo_venta=self.instance.equipo_venta
            ).union(
                User.objects.filter(id=self.instance.usuario.id)
            )


# ============================================================
# FORMULARIOS PARA PROYECTOS
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

    equipos_venta = forms.ModelMultipleChoiceField(
        queryset=EquipoVenta.objects.filter(activo=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        required=False,
        label="Equipos de Venta Asignados",
        help_text="Equipos que podrán vender inmuebles de este proyecto"
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

        # Si estamos editando, cargar los equipos actuales
        if self.instance.pk:
            self.fields['equipos_venta'].initial = self.instance.equipos_venta.filter(
                asignacionequipoproyecto__activo=True
            )

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        proyecto = super().save(commit=commit)

        if commit:
            # Gestionar asignaciones de equipos de venta
            equipos_seleccionados = self.cleaned_data.get('equipos_venta', [])

            # Desactivar asignaciones actuales
            AsignacionEquipoProyecto.objects.filter(
                proyecto=proyecto
            ).update(activo=False)

            # Crear nuevas asignaciones
            for equipo in equipos_seleccionados:
                AsignacionEquipoProyecto.objects.update_or_create(
                    proyecto=proyecto,
                    equipo_venta=equipo,
                    defaults={'activo': True}
                )

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
            }),
            'disponible': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }
        labels = {
            'codigo': 'Código del Inmueble',
            'tipo': 'Tipo de Inmueble',
            'm2': 'Metros Cuadrados (m²)',
            'precio_base': 'Precio Base (COP)',
            'precio_venta': 'Precio de Venta (COP)',
            'estado': 'Estado',
            'piso': 'Piso',
            'orientacion': 'Orientación',
            'caracteristicas': 'Características',
            'disponible': 'Disponible para Venta'
        }
        help_texts = {
            'codigo': 'Código único del inmueble (ej: A-101, Torre1-502)',
            'area_terreno': 'Solo aplica para casas y algunos tipos de inmuebles',
            'precio_base': 'Precio base sin descuentos ni promociones',
            'precio_venta': 'Precio final de venta al público',
            'piso': 'Número de piso (0 para planta baja)',
            'caracteristicas': 'Características especiales, acabados, vista, etc.'
        }

    def clean(self):
        cleaned_data = super().clean()
        precio_base = cleaned_data.get('precio_base')
        precio_venta = cleaned_data.get('precio_venta')

        if precio_base and precio_venta and precio_venta < precio_base:
            raise ValidationError({
                'precio_venta': 'El precio de venta no puede ser menor al precio base.'
            })

        return cleaned_data


# ============================================================
# FORMULARIOS PARA COMISIONES
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
        help_texts = {
            'porcentaje_gerente_proyecto': 'Porcentaje de comisión para el gerente del proyecto',
            'porcentaje_jefe_proyecto': 'Porcentaje de comisión para el jefe del proyecto'
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


class ComisionVentaForm(forms.ModelForm):
    """Formulario para configurar comisiones de venta"""

    class Meta:
        model = ComisionVenta
        fields = [
            'porcentaje_gerente_equipo', 'porcentaje_jefe_venta',
            'porcentaje_team_leader', 'porcentaje_vendedor', 'activo'
        ]
        widgets = {
            'porcentaje_gerente_equipo': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'porcentaje_jefe_venta': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'porcentaje_team_leader': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'porcentaje_vendedor': forms.NumberInput(attrs={
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
            'porcentaje_gerente_equipo': 'Comisión Gerente de Equipo (%)',
            'porcentaje_jefe_venta': 'Comisión Jefe de Venta (%)',
            'porcentaje_team_leader': 'Comisión Team Leader (%)',
            'porcentaje_vendedor': 'Comisión Vendedor (%)',
            'activo': 'Configuración Activa'
        }
        help_texts = {
            'porcentaje_gerente_equipo': 'Porcentaje de comisión para el gerente del equipo',
            'porcentaje_jefe_venta': 'Porcentaje de comisión para el jefe de venta',
            'porcentaje_team_leader': 'Porcentaje de comisión para el team leader',
            'porcentaje_vendedor': 'Porcentaje de comisión para el vendedor'
        }

    def clean(self):
        cleaned_data = super().clean()
        porcentajes = [
            cleaned_data.get('porcentaje_gerente_equipo', 0),
            cleaned_data.get('porcentaje_jefe_venta', 0),
            cleaned_data.get('porcentaje_team_leader', 0),
            cleaned_data.get('porcentaje_vendedor', 0),
        ]

        total = sum(porcentajes)
        if total > 100:
            raise ValidationError(
                f'La suma de todos los porcentajes ({total}%) no puede exceder 100%.'
            )

        return cleaned_data


# ============================================================
# FORMULARIOS PARA BÚSQUEDA Y FILTROS
# ============================================================

class EquipoVentaFilterForm(forms.Form):
    """Formulario para filtrar equipos de venta"""

    nombre = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Buscar por nombre...'
        }),
        label='Nombre'
    )

    activo = forms.ChoiceField(
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