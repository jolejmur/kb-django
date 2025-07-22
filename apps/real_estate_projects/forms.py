# apps/real_estate_projects/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import models
from .models import Proyecto, Fase, GerenteProyecto, JefeProyecto, Inmueble, Ponderador
from decimal import Decimal

User = get_user_model()


class ProyectoForm(forms.ModelForm):
    """Formulario para crear/editar proyectos"""
    
    # Campo adicional para número de fases
    numero_fases = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        help_text="Número de fases del proyecto (se crearán automáticamente)"
    )
    
    # Campos para estructura de departamentos
    numero_torres = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        required=False,
        help_text="Número de torres por fase"
    )
    
    pisos_inicio = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=1,
        required=False,
        help_text="Número del piso de inicio"
    )
    
    pisos_fin = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=10,
        required=False,
        help_text="Número del piso final"
    )
    
    departamentos_por_piso = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=4,
        required=False,
        help_text="Número de departamentos por piso"
    )
    
    # Campos para estructura de terrenos
    numero_sectores = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        required=False,
        help_text="Número de sectores por fase"
    )
    
    manzanas_inicio = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        required=False,
        help_text="Número de manzana de inicio"
    )
    
    manzanas_fin = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=10,
        required=False,
        help_text="Número de manzana final"
    )
    
    terrenos_por_manzana = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=8,
        required=False,
        help_text="Número de terrenos por manzana"
    )
    
    # Campos para selección de usuarios
    gerente_usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=True,
        empty_label="Seleccionar gerente de proyecto",
        label="Gerente de Proyecto"
    )
    
    jefe_usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="Seleccionar jefe de proyecto (opcional)",
        label="Jefe de Proyecto"
    )
    
    class Meta:
        model = Proyecto
        fields = [
            'nombre', 'descripcion', 'tipo', 'estado', 'precio_base_m2'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Nombre del proyecto'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Descripción del proyecto'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'estado': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'precio_base_m2': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Precio base por m² (ej: 1000.00)'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aplicar clases CSS a los campos de usuario
        self.fields['gerente_usuario'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
        
        self.fields['jefe_usuario'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
        
        # Aplicar clases CSS a todos los campos de estructura
        structure_fields = [
            'numero_fases', 'numero_torres', 'pisos_inicio', 'pisos_fin', 
            'departamentos_por_piso', 'numero_sectores', 'manzanas_inicio', 
            'manzanas_fin', 'terrenos_por_manzana'
        ]
        
        for field_name in structure_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                    'min': '1'
                })
        
        # Si estamos editando, prellenar los campos de usuario y ajustar requerimientos
        if self.instance.pk:
            if self.instance.gerente_proyecto:
                self.fields['gerente_usuario'].initial = self.instance.gerente_proyecto.usuario
            if self.instance.jefe_proyecto:
                self.fields['jefe_usuario'].initial = self.instance.jefe_proyecto.usuario
            
            # En modo edición, numero_fases no debe ser requerido ya que las fases ya existen
            self.fields['numero_fases'].required = False

    def clean(self):
        cleaned_data = super().clean()
        gerente_usuario = cleaned_data.get('gerente_usuario')
        tipo_proyecto = cleaned_data.get('tipo')
        
        # Debug: mostrar todos los datos recibidos
        import sys
        print(f"=== DEBUG CLEAN ===", file=sys.stderr)
        print(f"CLEANED_DATA COMPLETO: {cleaned_data}", file=sys.stderr)
        print(f"SELF.DATA COMPLETO: {dict(self.data) if hasattr(self, 'data') else 'No data'}", file=sys.stderr)
        
        # Validar gerente de proyecto (requerido)
        if not gerente_usuario:
            raise ValidationError({'gerente_usuario': 'El gerente de proyecto es requerido.'})
        
        # Procesar datos de estructura dinámica desde el POST
        if hasattr(self, 'data'):
            structure_data = self._parse_dynamic_structure(tipo_proyecto)
            cleaned_data['dynamic_structure_data'] = structure_data
        
        return cleaned_data
    
    def _parse_dynamic_structure(self, tipo_proyecto):
        """Parsear la estructura dinámica REAL del formulario"""
        import sys
        
        print(f"=== PARSEANDO ESTRUCTURA DINÁMICA ===", file=sys.stderr)
        print(f"TODOS LOS CAMPOS DEL FORMULARIO:", file=sys.stderr)
        for key, value in self.data.items():
            if 'ponderador' in key.lower():
                print(f"  {key} = {value}", file=sys.stderr)
        
        structure_data = {'fases': {}, 'ponderadores': []}
        
        # 1. PARSEAR PONDERADORES DEL PROYECTO (NUEVOS)
        print(f"=== PARSEANDO PONDERADORES NUEVOS ===", file=sys.stderr)
        for key, value in self.data.items():
            if key.startswith('ponderador_') and key.endswith('_nombre'):
                ponderador_num = key.split('_')[1]
                nombre = value.strip()
                
                if nombre:  # Solo procesar si hay nombre
                    tipo = self.data.get(f'ponderador_{ponderador_num}_tipo', 'valorizacion')
                    porcentaje = self.data.get(f'ponderador_{ponderador_num}_porcentaje', '0')
                    monto_fijo = self.data.get(f'ponderador_{ponderador_num}_monto_fijo', '')
                    descripcion = self.data.get(f'ponderador_{ponderador_num}_descripcion', '')
                    nivel = self.data.get(f'ponderador_{ponderador_num}_nivel', 'proyecto')
                    
                    try:
                        porcentaje_val = float(porcentaje) if porcentaje else 0
                        monto_fijo_val = float(monto_fijo) if monto_fijo else None
                    except ValueError:
                        porcentaje_val = 0
                        monto_fijo_val = None
                    
                    ponderador_data = {
                        'nombre': nombre,
                        'tipo': tipo,
                        'porcentaje': porcentaje_val,
                        'monto_fijo': monto_fijo_val,
                        'descripcion': descripcion,
                        'nivel_aplicacion': nivel
                    }
                    
                    structure_data['ponderadores'].append(ponderador_data)
                    print(f"  NUEVO PONDERADOR: {nombre} ({tipo}) - {porcentaje_val}%", file=sys.stderr)
        
        # 1.5. PARSEAR PONDERADORES EXISTENTES
        print(f"=== PARSEANDO PONDERADORES EXISTENTES ===", file=sys.stderr)
        existing_ponderadores = []
        for key, value in self.data.items():
            if key.startswith('existing_ponderador_') and key.endswith('_id'):
                ponderador_id = value.strip()
                
                if ponderador_id:  # Solo procesar si hay ID
                    nombre = self.data.get(f'existing_ponderador_{ponderador_id}_nombre', '').strip()
                    tipo = self.data.get(f'existing_ponderador_{ponderador_id}_tipo', 'valorizacion')
                    porcentaje = self.data.get(f'existing_ponderador_{ponderador_id}_porcentaje', '0')
                    monto_fijo = self.data.get(f'existing_ponderador_{ponderador_id}_monto_fijo', '')
                    descripcion = self.data.get(f'existing_ponderador_{ponderador_id}_descripcion', '')
                    activo = self.data.get(f'existing_ponderador_{ponderador_id}_activo') == 'on'
                    
                    try:
                        porcentaje_val = float(porcentaje) if porcentaje else 0
                        monto_fijo_val = float(monto_fijo) if monto_fijo else None
                    except ValueError:
                        porcentaje_val = 0
                        monto_fijo_val = None
                    
                    existing_ponderador = {
                        'id': int(ponderador_id),
                        'nombre': nombre,
                        'tipo': tipo,
                        'porcentaje': porcentaje_val,
                        'monto_fijo': monto_fijo_val,
                        'descripcion': descripcion,
                        'activo': activo
                    }
                    
                    existing_ponderadores.append(existing_ponderador)
                    print(f"  EXISTING PONDERADOR: {nombre} (ID: {ponderador_id}) - {porcentaje_val}% - Activo: {activo}", file=sys.stderr)
        
        structure_data['existing_ponderadores'] = existing_ponderadores
        
        # 2. PARSEAR PONDERADORES DE FASE (NUEVOS)
        print(f"=== PARSEANDO PONDERADORES DE FASE ===", file=sys.stderr)
        ponderadores_fase = []
        for key, value in self.data.items():
            if key.startswith('fase_') and '_ponderador_' in key and key.endswith('_nombre'):
                # Parsear: fase_X_ponderador_Y_nombre
                parts = key.split('_')
                if len(parts) >= 4:
                    fase_num = int(parts[1])
                    ponderador_num = int(parts[3])
                    nombre = value.strip()
                    
                    if nombre:  # Solo procesar si hay nombre
                        ponderador_id = f"fase_{fase_num}_ponderador_{ponderador_num}"
                        tipo = self.data.get(f'{ponderador_id}_tipo', 'valorizacion')
                        porcentaje = self.data.get(f'{ponderador_id}_porcentaje', '0')
                        monto_fijo = self.data.get(f'{ponderador_id}_monto_fijo', '')
                        descripcion = self.data.get(f'{ponderador_id}_descripcion', '')
                        
                        try:
                            porcentaje_val = float(porcentaje) if porcentaje else 0
                            monto_fijo_val = float(monto_fijo) if monto_fijo else None
                        except ValueError:
                            porcentaje_val = 0
                            monto_fijo_val = None
                        
                        ponderador_fase_data = {
                            'nombre': nombre,
                            'tipo': tipo,
                            'porcentaje': porcentaje_val,
                            'monto_fijo': monto_fijo_val,
                            'descripcion': descripcion,
                            'nivel_aplicacion': 'fase',
                            'fase_numero': fase_num
                        }
                        
                        ponderadores_fase.append(ponderador_fase_data)
                        print(f"  PONDERADOR FASE {fase_num}: {nombre} ({tipo}) - {porcentaje_val}%", file=sys.stderr)
        
        structure_data['ponderadores_fase'] = ponderadores_fase
        
        # 3. PARSEAR COMERCIALIZACIÓN DE FASES
        print(f"=== PARSEANDO COMERCIALIZACIÓN ===", file=sys.stderr)
        for key, value in self.data.items():
            if key.startswith('fase_') and key.endswith('_comercializable'):
                parts = key.split('_')
                if len(parts) >= 2:
                    fase_num = int(parts[1])
                    comercializable = value == 'on'
                    
                    # Inicializar fase si no existe
                    if fase_num not in structure_data['fases']:
                        structure_data['fases'][fase_num] = {
                            'nombre': f'Fase {fase_num}',
                            'comercializable': comercializable,
                            'torres': {},
                            'sectores': {}
                        }
                    else:
                        structure_data['fases'][fase_num]['comercializable'] = comercializable
                    
                    print(f"  FASE {fase_num}: comercializable = {comercializable}", file=sys.stderr)
        
        # 4. PARSEAR ESTRUCTURA DE DEPARTAMENTOS
        print(f"=== PARSEANDO DEPARTAMENTOS ===", file=sys.stderr)
        for key, value in self.data.items():
            if key.startswith('fase_') and 'departamentos' in key:
                print(f"CAMPO ENCONTRADO: {key} = {value}", file=sys.stderr)
                
                # Parsear el nombre del campo: fase_X_torre_Y_piso_Z_departamentos
                parts = key.split('_')
                if len(parts) >= 6:
                    fase_num = int(parts[1])
                    torre_num = int(parts[3])
                    piso_num = int(parts[5])
                    departamentos = int(value) if value else 0
                    
                    # Inicializar fase si no existe
                    if fase_num not in structure_data['fases']:
                        structure_data['fases'][fase_num] = {
                            'nombre': f'Fase {fase_num}',
                            'comercializable': False,
                            'torres': {},
                            'sectores': {}
                        }
                    
                    # Inicializar torre si no existe
                    if torre_num not in structure_data['fases'][fase_num]['torres']:
                        structure_data['fases'][fase_num]['torres'][torre_num] = {
                            'nombre': f'Torre {torre_num}',
                            'pisos': {},
                            'comercializable': False
                        }
                    
                    # Agregar piso con departamentos
                    structure_data['fases'][fase_num]['torres'][torre_num]['pisos'][piso_num] = departamentos
                    
                    print(f"  AGREGADO: Fase {fase_num}, Torre {torre_num}, Piso {piso_num} = {departamentos} deptos", file=sys.stderr)
        
        # 5. PARSEAR ESTRUCTURA DE TERRENOS
        print(f"=== PARSEANDO TERRENOS ===", file=sys.stderr)
        for key, value in self.data.items():
            if key.startswith('fase_') and 'terrenos' in key:
                print(f"CAMPO TERRENOS: {key} = {value}", file=sys.stderr)
                
                # Parsear: fase_X_sector_Y_manzana_Z_terrenos
                parts = key.split('_')
                if len(parts) >= 6:
                    fase_num = int(parts[1])
                    sector_num = int(parts[3])
                    manzana_num = int(parts[5])
                    terrenos = int(value) if value else 0
                    
                    # Inicializar fase si no existe
                    if fase_num not in structure_data['fases']:
                        structure_data['fases'][fase_num] = {
                            'nombre': f'Fase {fase_num}',
                            'comercializable': False,
                            'torres': {},
                            'sectores': {}
                        }
                    
                    # Inicializar sector si no existe
                    if sector_num not in structure_data['fases'][fase_num]['sectores']:
                        structure_data['fases'][fase_num]['sectores'][sector_num] = {
                            'nombre': f'Sector {sector_num}',
                            'manzanas': {},
                            'comercializable': False
                        }
                    
                    # Agregar manzana con terrenos
                    structure_data['fases'][fase_num]['sectores'][sector_num]['manzanas'][manzana_num] = terrenos
                    
                    print(f"  TERRENO: Fase {fase_num}, Sector {sector_num}, Manzana {manzana_num} = {terrenos} terrenos", file=sys.stderr)
        
        # 5. CONVERTIR A FORMATO ESPERADO POR LAS FUNCIONES DE CREACIÓN
        
        # Convertir torres
        for fase_num, fase_data in structure_data['fases'].items():
            if fase_data['torres']:
                for torre_num, torre_data in fase_data['torres'].items():
                    pisos = torre_data['pisos']
                    if pisos:
                        pisos_nums = list(pisos.keys())
                        torre_data['pisos_inicio'] = min(pisos_nums)
                        torre_data['pisos_fin'] = max(pisos_nums)
                        # Para simplificar, usar el valor del primer piso
                        torre_data['deptos_piso'] = list(pisos.values())[0]
                        
                        print(f"  TORRE {torre_num}: pisos {torre_data['pisos_inicio']}-{torre_data['pisos_fin']}, {torre_data['deptos_piso']} deptos/piso", file=sys.stderr)
        
        # Convertir sectores
        for fase_num, fase_data in structure_data['fases'].items():
            if fase_data['sectores']:
                for sector_num, sector_data in fase_data['sectores'].items():
                    manzanas = sector_data['manzanas']
                    if manzanas:
                        manzanas_nums = list(manzanas.keys())
                        sector_data['manzanas_inicio'] = min(manzanas_nums)
                        sector_data['manzanas_fin'] = max(manzanas_nums)
                        # Para simplificar, usar el valor de la primera manzana
                        sector_data['terrenos_manzana'] = list(manzanas.values())[0]
                        
                        print(f"  SECTOR {sector_num}: manzanas {sector_data['manzanas_inicio']}-{sector_data['manzanas_fin']}, {sector_data['terrenos_manzana']} terrenos/manzana", file=sys.stderr)
        
        print(f"ESTRUCTURA DINÁMICA PARSEADA: {len(structure_data['fases'])} fases, {len(structure_data['ponderadores'])} ponderadores", file=sys.stderr)
        print(f"ESTRUCTURA COMPLETA: {structure_data}", file=sys.stderr)
        
        return structure_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Crear o obtener GerenteProyecto
        gerente_usuario = self.cleaned_data.get('gerente_usuario')
        if gerente_usuario:
            gerente_obj, created = GerenteProyecto.objects.get_or_create(
                usuario=gerente_usuario,
                defaults={'activo': True}
            )
            instance.gerente_proyecto = gerente_obj
        
        # Crear o obtener JefeProyecto (opcional)
        jefe_usuario = self.cleaned_data.get('jefe_usuario')
        if jefe_usuario:
            # Necesitamos el gerente_proyecto para crear el jefe
            jefe_obj, created = JefeProyecto.objects.get_or_create(
                usuario=jefe_usuario,
                defaults={'activo': True, 'gerente_proyecto': instance.gerente_proyecto}
            )
            # Si ya existía pero no tenía gerente, asignarlo
            if not created and not jefe_obj.gerente_proyecto and instance.gerente_proyecto:
                jefe_obj.gerente_proyecto = instance.gerente_proyecto
                jefe_obj.save()
            instance.jefe_proyecto = jefe_obj
        else:
            instance.jefe_proyecto = None
        
        if commit:
            instance.save()
        
        return instance


class InmuebleForm(forms.ModelForm):
    """Formulario para crear/editar inmuebles individuales"""
    
    # Campos para selección jerárquica
    proyecto = forms.ModelChoiceField(
        queryset=None,
        required=True,
        empty_label="Seleccionar proyecto",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'data-cascade': 'proyecto'
        })
    )
    
    fase = forms.ModelChoiceField(
        queryset=None,
        required=True,
        empty_label="Seleccionar fase",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'data-cascade': 'fase',
            'disabled': True
        })
    )
    
    # Para departamentos
    torre = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Seleccionar torre",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'data-cascade': 'torre',
            'disabled': True
        })
    )
    
    piso = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Seleccionar piso",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'data-cascade': 'piso',
            'disabled': True
        })
    )
    
    # Para terrenos
    sector = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Seleccionar sector",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'data-cascade': 'sector',
            'disabled': True
        })
    )
    
    manzana = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Seleccionar manzana",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'data-cascade': 'manzana',
            'disabled': True
        })
    )
    
    # Campo para gestionar ponderadores
    ponderadores = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label="Ponderadores de Precio",
        help_text="Selecciona los ponderadores que aplican a este inmueble"
    )

    class Meta:
        model = None  # Se establecerá dinámicamente
        fields = [
            'codigo', 'tipo', 'm2', 
            'factor_precio', 'precio_manual', 'estado', 
            'caracteristicas', 'disponible_comercializacion', 'ponderadores'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Código único del inmueble'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'm2': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Área en metros cuadrados'
            }),
            'factor_precio': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.0001',
                'min': '0.0001',
                'value': '1.0000'
            }),
            'precio_manual': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Precio manual (opcional)'
            }),
            'estado': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'caracteristicas': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Características adicionales del inmueble'
            }),
            'disponible_comercializacion': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
            })
        }

    def __init__(self, *args, **kwargs):
        # Importar aquí para evitar import circular
        from .models import Proyecto, Fase, Torre, Piso, Sector, Manzana, Inmueble
        
        self._meta.model = Inmueble
        
        proyecto_id = kwargs.pop('proyecto_id', None)
        fase_id = kwargs.pop('fase_id', None)
        super().__init__(*args, **kwargs)
        
        # Configurar querysets iniciales
        self.fields['proyecto'].queryset = Proyecto.objects.filter(activo=True)
        self.fields['fase'].queryset = Fase.objects.none()
        self.fields['torre'].queryset = Torre.objects.none()
        self.fields['piso'].queryset = Piso.objects.none()
        self.fields['sector'].queryset = Sector.objects.none()
        self.fields['manzana'].queryset = Manzana.objects.none()
        self.fields['ponderadores'].queryset = Ponderador.objects.none()
        
        # Si hay parámetros iniciales, precargar
        if proyecto_id:
            try:
                proyecto = Proyecto.objects.get(pk=proyecto_id, activo=True)
                self.fields['proyecto'].initial = proyecto
                self.fields['fase'].queryset = proyecto.fases.filter(activo=True)
                self.fields['fase'].widget.attrs.pop('disabled', None)
                
                # Configurar ponderadores del proyecto
                ponderadores_aplicables = Ponderador.objects.filter(
                    activo=True,
                    proyecto=proyecto
                ).filter(
                    # Ponderadores de proyecto (aplican a todos)
                    models.Q(nivel_aplicacion='proyecto') |
                    # Ponderadores de inmueble específico
                    models.Q(nivel_aplicacion='inmueble')
                ).order_by('nivel_aplicacion', 'nombre')
                
                self.fields['ponderadores'].queryset = ponderadores_aplicables

                if fase_id and proyecto.tipo == 'departamentos':
                    fase = Fase.objects.get(pk=fase_id, proyecto=proyecto, activo=True)
                    self.fields['fase'].initial = fase
                    self.fields['torre'].queryset = fase.torres.filter(activo=True)
                    self.fields['torre'].widget.attrs.pop('disabled', None)
                    
                    # Agregar ponderadores de fase específica
                    ponderadores_con_fase = Ponderador.objects.filter(
                        activo=True,
                        proyecto=proyecto
                    ).filter(
                        models.Q(nivel_aplicacion='proyecto') |
                        models.Q(nivel_aplicacion='fase', fase=fase) |
                        models.Q(nivel_aplicacion='inmueble')
                    ).order_by('nivel_aplicacion', 'nombre')
                    
                    self.fields['ponderadores'].queryset = ponderadores_con_fase
                    
                elif fase_id and proyecto.tipo == 'terrenos':
                    fase = Fase.objects.get(pk=fase_id, proyecto=proyecto, activo=True)
                    self.fields['fase'].initial = fase
                    self.fields['sector'].queryset = fase.sectores.filter(activo=True)
                    self.fields['sector'].widget.attrs.pop('disabled', None)
                    
                    # Agregar ponderadores de fase específica
                    ponderadores_con_fase = Ponderador.objects.filter(
                        activo=True,
                        proyecto=proyecto
                    ).filter(
                        models.Q(nivel_aplicacion='proyecto') |
                        models.Q(nivel_aplicacion='fase', fase=fase) |
                        models.Q(nivel_aplicacion='inmueble')
                    ).order_by('nivel_aplicacion', 'nombre')
                    
                    self.fields['ponderadores'].queryset = ponderadores_con_fase
                    
            except (Proyecto.DoesNotExist, Fase.DoesNotExist):
                pass

    def clean(self):
        cleaned_data = super().clean()
        proyecto = cleaned_data.get('proyecto')
        fase = cleaned_data.get('fase')
        
        if proyecto and fase:
            # Validar que la fase pertenezca al proyecto
            if fase.proyecto != proyecto:
                raise ValidationError('La fase seleccionada no pertenece al proyecto.')
            
            # Validar campos específicos según el tipo de proyecto
            if proyecto.tipo == 'departamentos':
                torre = cleaned_data.get('torre')
                piso = cleaned_data.get('piso')
                
                if not torre:
                    raise ValidationError('Para proyectos de departamentos debe seleccionar una torre.')
                if not piso:
                    raise ValidationError('Para proyectos de departamentos debe seleccionar un piso.')
                if torre.fase != fase:
                    raise ValidationError('La torre seleccionada no pertenece a la fase.')
                if piso.torre != torre:
                    raise ValidationError('El piso seleccionado no pertenece a la torre.')
                
                # Limpiar campos de terrenos
                cleaned_data['sector'] = None
                cleaned_data['manzana'] = None
                
            elif proyecto.tipo == 'terrenos':
                sector = cleaned_data.get('sector')
                manzana = cleaned_data.get('manzana')
                
                if not sector:
                    raise ValidationError('Para proyectos de terrenos debe seleccionar un sector.')
                if not manzana:
                    raise ValidationError('Para proyectos de terrenos debe seleccionar una manzana.')
                if sector.fase != fase:
                    raise ValidationError('El sector seleccionado no pertenece a la fase.')
                if manzana.sector != sector:
                    raise ValidationError('La manzana seleccionada no pertenece al sector.')
                
                # Limpiar campos de departamentos
                cleaned_data['torre'] = None
                cleaned_data['piso'] = None
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asignar las relaciones correctas
        fase = self.cleaned_data.get('fase')
        instance.fase = fase
        
        if fase.proyecto.tipo == 'departamentos':
            instance.piso = self.cleaned_data.get('piso')
            instance.manzana = None
        elif fase.proyecto.tipo == 'terrenos':
            instance.manzana = self.cleaned_data.get('manzana')
            instance.piso = None
        
        if commit:
            instance.save()
            # Manejar ponderadores many-to-many
            self.save_m2m()
        
        return instance


class InmuebleEditForm(forms.ModelForm):
    """Formulario mejorado para editar inmuebles existentes
    Permite editar más campos y gestionar ponderadores"""
    
    # Campos de solo lectura para mostrar información
    proyecto_info = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-600',
            'readonly': True,
            'placeholder': 'Información del proyecto'
        })
    )
    
    fase_info = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-600',
            'readonly': True,
            'placeholder': 'Información de la fase'
        })
    )
    
    codigo_info = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-600',
            'readonly': True,
            'placeholder': 'Código del inmueble'
        })
    )
    
    tipo_info = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-600',
            'readonly': True,
            'placeholder': 'Tipo de inmueble'
        })
    )
    
    # Campo para gestionar ponderadores
    ponderadores = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label="Ponderadores de Precio"
    )
    
    class Meta:
        model = Inmueble
        fields = [
            'm2', 'estado', 'caracteristicas', 'disponible_comercializacion', 'ponderadores'
        ]
        widgets = {
            'm2': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Área en metros cuadrados'
            }),
            'factor_precio': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.0001',
                'min': '0.0001',
                'placeholder': 'Factor multiplicador (ej: 1.0000)'
            }),
            'precio_manual': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Precio manual (opcional - sobrescribe cálculo automático)'
            }),
            'estado': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'caracteristicas': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Características adicionales del inmueble'
            }),
            'disponible_comercializacion': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si hay una instancia, llenar los campos de información
        if self.instance and self.instance.pk:
            self.fields['codigo_info'].initial = self.instance.codigo
            self.fields['tipo_info'].initial = self.instance.get_tipo_display()
            
            if self.instance.fase:
                proyecto = self.instance.fase.proyecto
                fase = self.instance.fase
                
                self.fields['proyecto_info'].initial = f"{proyecto.nombre} ({proyecto.get_tipo_display()})"
                self.fields['fase_info'].initial = f"{fase.nombre} - Fase {fase.numero_fase}"
                
                # Configurar queryset de ponderadores - solo los aplicables a este inmueble
                ponderadores_aplicables = Ponderador.objects.filter(
                    activo=True,
                    proyecto=proyecto
                ).filter(
                    # Ponderadores de proyecto (aplican a todos)
                    models.Q(nivel_aplicacion='proyecto') |
                    # Ponderadores de fase específica de este inmueble
                    models.Q(nivel_aplicacion='fase', fase=fase) |
                    # Ponderadores de inmueble específico
                    models.Q(nivel_aplicacion='inmueble')
                ).order_by('nivel_aplicacion', 'nombre')
                
                self.fields['ponderadores'].queryset = ponderadores_aplicables
        else:
            # Si no hay instancia, mostrar todos los ponderadores activos
            self.fields['ponderadores'].queryset = Ponderador.objects.filter(activo=True).order_by('nombre')

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            # Manejar ponderadores many-to-many
            self.save_m2m()
        
        return instance


class FaseForm(forms.ModelForm):
    """Formulario para crear/editar fases"""
    
    class Meta:
        model = Fase
        fields = [
            'nombre', 'descripcion', 'numero_fase', 'fecha_inicio_prevista',
            'fecha_entrega_prevista', 'precio_m2'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Nombre de la fase'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Descripción de la fase'
            }),
            'numero_fase': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'min': '1'
            }),
            'fecha_inicio_prevista': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'type': 'date'
            }),
            'fecha_entrega_prevista': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'type': 'date'
            }),
            'precio_m2': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Precio por m²'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio_prevista')
        fecha_entrega = cleaned_data.get('fecha_entrega_prevista')

        if fecha_inicio and fecha_entrega and fecha_inicio > fecha_entrega:
            raise ValidationError('La fecha de inicio no puede ser posterior a la fecha de entrega.')

        return cleaned_data


class ComercializacionFaseForm(forms.Form):
    """Formulario para gestionar la comercialización de inmuebles en una fase"""
    
    comercializable = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label="Marcar todos los inmuebles de esta fase como comercializables"
    )

    def __init__(self, *args, **kwargs):
        self.fase = kwargs.pop('fase', None)
        super().__init__(*args, **kwargs)
        
        if self.fase:
            # Verificar estado actual de comercialización
            total_inmuebles = self.fase.inmuebles.count()
            comercializables = self.fase.inmuebles.filter(disponible_comercializacion=True).count()
            
            if total_inmuebles > 0 and comercializables == total_inmuebles:
                self.fields['comercializable'].initial = True
            
            # Actualizar la etiqueta con información específica
            self.fields['comercializable'].label = (
                f"Marcar todos los inmuebles de la fase '{self.fase.nombre}' como comercializables "
                f"({comercializables}/{total_inmuebles} actualmente comercializables)"
            )

    def save(self):
        if self.fase and self.is_valid():
            comercializable = self.cleaned_data.get('comercializable', False)
            return self.fase.marcar_comercializable(comercializable)
        return 0


class ComercializacionTorreForm(forms.Form):
    """Formulario para gestionar la comercialización de inmuebles en una torre"""
    
    comercializable = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label="Marcar todos los inmuebles de esta torre como comercializables"
    )

    def __init__(self, *args, **kwargs):
        self.torre = kwargs.pop('torre', None)
        super().__init__(*args, **kwargs)
        
        if self.torre:
            # Verificar estado actual de comercialización
            from .models import Inmueble
            total_inmuebles = Inmueble.objects.filter(piso__torre=self.torre).count()
            comercializables = Inmueble.objects.filter(
                piso__torre=self.torre,
                disponible_comercializacion=True
            ).count()
            
            if total_inmuebles > 0 and comercializables == total_inmuebles:
                self.fields['comercializable'].initial = True
            
            # Actualizar la etiqueta con información específica
            self.fields['comercializable'].label = (
                f"Marcar todos los inmuebles de la torre '{self.torre.nombre}' como comercializables "
                f"({comercializables}/{total_inmuebles} actualmente comercializables)"
            )

    def save(self):
        if self.torre and self.is_valid():
            comercializable = self.cleaned_data.get('comercializable', False)
            return self.torre.marcar_comercializable(comercializable)
        return 0


class ComercializacionSectorForm(forms.Form):
    """Formulario para gestionar la comercialización de inmuebles en un sector"""
    
    comercializable = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'
        }),
        label="Marcar todos los inmuebles de este sector como comercializables"
    )

    def __init__(self, *args, **kwargs):
        self.sector = kwargs.pop('sector', None)
        super().__init__(*args, **kwargs)
        
        if self.sector:
            # Verificar estado actual de comercialización
            from .models import Inmueble
            total_inmuebles = Inmueble.objects.filter(manzana__sector=self.sector).count()
            comercializables = Inmueble.objects.filter(
                manzana__sector=self.sector,
                disponible_comercializacion=True
            ).count()
            
            if total_inmuebles > 0 and comercializables == total_inmuebles:
                self.fields['comercializable'].initial = True
            
            # Actualizar la etiqueta con información específica
            self.fields['comercializable'].label = (
                f"Marcar todos los inmuebles del sector '{self.sector.nombre}' como comercializables "
                f"({comercializables}/{total_inmuebles} actualmente comercializables)"
            )

    def save(self):
        if self.sector and self.is_valid():
            comercializable = self.cleaned_data.get('comercializable', False)
            return self.sector.marcar_comercializable(comercializable)
        return 0


class PonderadorForm(forms.ModelForm):
    """Formulario para crear/editar ponderadores de precio jerárquicos"""
    
    # Campo para seleccionar el tipo de valor
    tipo_valor = forms.ChoiceField(
        choices=[
            ('porcentaje', 'Porcentaje'),
            ('monto_fijo', 'Monto Fijo'),
        ],
        initial='porcentaje',
        widget=forms.RadioSelect(attrs={
            'class': 'radio-group'
        }),
        label="Tipo de Ajuste"
    )
    
    # Campo para mostrar precio base calculado automáticamente
    precio_base_calculado = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-600',
            'readonly': True,
            'placeholder': 'Se calculará automáticamente'
        }),
        label="Precio Base (m²)"
    )
    
    class Meta:
        model = Ponderador
        fields = [
            'nombre', 'tipo', 'nivel_aplicacion', 'fase',
            'porcentaje', 'monto_fijo', 'descripcion', 'justificacion',
            'fecha_activacion', 'fecha_desactivacion'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Nombre del ponderador (ej: Nuevo puente, Descuento lanzamiento)'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'nivel_aplicacion': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'onchange': 'toggleFaseField(this.value)'
            }),
            'fase': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'porcentaje': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '-100.00',
                'max': '500.00',
                'placeholder': 'Ej: 15.00 = +15%, -5.00 = -5%'
            }),
            'monto_fijo': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Monto en pesos'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Descripción detallada del ponderador'
            }),
            'justificacion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'Razón o justificación para este ponderador'
            }),
            'fecha_activacion': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'type': 'datetime-local'
            }),
            'fecha_desactivacion': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'type': 'datetime-local'
            })
        }

    def __init__(self, *args, **kwargs):
        self.proyecto = kwargs.pop('proyecto', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Configurar queryset de fases
        if self.proyecto:
            self.fields['fase'].queryset = self.proyecto.fases.filter(activo=True).order_by('numero_fase')
        else:
            self.fields['fase'].queryset = Fase.objects.none()
        
        # Configurar tipo_valor inicial basado en los datos existentes
        if self.instance.pk:
            if self.instance.monto_fijo:
                self.fields['tipo_valor'].initial = 'monto_fijo'
            else:
                self.fields['tipo_valor'].initial = 'porcentaje'
            
            # Mostrar precio base si está disponible
            if self.proyecto and self.proyecto.precio_base_m2:
                self.fields['precio_base_calculado'].initial = f"${self.proyecto.precio_base_m2:,.2f}"
        
        # Configurar fechas por defecto
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['fecha_activacion'].initial = timezone.now()

    def clean(self):
        cleaned_data = super().clean()
        tipo_valor = cleaned_data.get('tipo_valor')
        porcentaje = cleaned_data.get('porcentaje')
        monto_fijo = cleaned_data.get('monto_fijo')
        nivel_aplicacion = cleaned_data.get('nivel_aplicacion')
        fase = cleaned_data.get('fase')
        
        # Validar que tenga porcentaje O monto fijo según el tipo seleccionado
        if tipo_valor == 'porcentaje':
            if not porcentaje:
                raise ValidationError('Debe especificar un porcentaje cuando el tipo es "Porcentaje".')
            cleaned_data['monto_fijo'] = None
        elif tipo_valor == 'monto_fijo':
            if not monto_fijo:
                raise ValidationError('Debe especificar un monto fijo cuando el tipo es "Monto Fijo".')
            cleaned_data['porcentaje'] = None
        
        # Validar nivel de aplicación y fase
        if nivel_aplicacion == 'fase' and not fase:
            raise ValidationError('Debe seleccionar una fase cuando el nivel de aplicación es "Solo la Fase".')
        elif nivel_aplicacion != 'fase':
            cleaned_data['fase'] = None
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asignar proyecto y usuario
        if self.proyecto:
            instance.proyecto = self.proyecto
        
        if self.user:
            if not instance.pk:  # Nuevo ponderador
                instance.created_by = self.user
                instance.activated_by = self.user
            # Para ediciones, el activated_by se actualiza en el método activar()
        
        if commit:
            instance.save()
        
        return instance


class PonderadorSimpleForm(forms.Form):
    """Formulario simplificado para crear ponderadores básicos en el formulario de proyecto"""
    
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Nombre del ponderador'
        })
    )
    
    monto_extra = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Monto extra'
        }),
        label="Monto Extra"
    )
    
    porcentaje_calculado = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-md text-gray-600',
            'readonly': True,
            'placeholder': 'Se calculará automáticamente'
        }),
        label="Porcentaje"
    )
    
    def __init__(self, *args, **kwargs):
        self.precio_base_m2 = kwargs.pop('precio_base_m2', Decimal('1000.00'))
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        monto_extra = cleaned_data.get('monto_extra')
        
        if monto_extra and self.precio_base_m2:
            # Calcular porcentaje automáticamente
            porcentaje = (monto_extra / self.precio_base_m2) * 100
            cleaned_data['porcentaje_calculado'] = f"{porcentaje:.2f}%"
        
        return cleaned_data
    
    def get_ponderador_data(self):
        """Devuelve los datos procesados para crear un ponderador"""
        if self.is_valid():
            monto_extra = self.cleaned_data.get('monto_extra')
            porcentaje = (monto_extra / self.precio_base_m2) * 100 if monto_extra and self.precio_base_m2 else 0
            
            return {
                'nombre': self.cleaned_data.get('nombre'),
                'monto_fijo': monto_extra,
                'porcentaje_calculado': porcentaje,
                'tipo': 'comercial',
                'nivel_aplicacion': 'proyecto'
            }
        return None