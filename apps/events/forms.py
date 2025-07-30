from django import forms
from django.utils import timezone
from .models import EventoComercial, VisitaEvento, InvitacionQR


class EventoComercialForm(forms.ModelForm):
    """Formulario para crear/editar eventos comerciales"""
    
    class Meta:
        model = EventoComercial
        fields = [
            'nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 
            'ubicacion', 'activo', 'permite_invitaciones', 'requiere_registro_cliente'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Nombre del evento'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Descripción del evento'
            }),
            'fecha_inicio': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'fecha_fin': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Ubicación del evento'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'permite_invitaciones': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'requiere_registro_cliente': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'nombre': 'Nombre del Evento',
            'descripcion': 'Descripción',
            'fecha_inicio': 'Fecha y Hora de Inicio',
            'fecha_fin': 'Fecha y Hora de Fin',
            'ubicacion': 'Ubicación',
            'activo': 'Evento Activo',
            'permite_invitaciones': 'Permitir Invitaciones',
            'requiere_registro_cliente': 'Requiere Registro de Cliente',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin:
            if fecha_inicio >= fecha_fin:
                raise forms.ValidationError('La fecha de fin debe ser posterior a la fecha de inicio.')
            
            # Verificar que no sea en el pasado (solo para eventos nuevos)
            if not self.instance.pk and fecha_inicio < timezone.now():
                raise forms.ValidationError('La fecha de inicio no puede ser en el pasado.')
        
        return cleaned_data


class VisitaEventoForm(forms.ModelForm):
    """Formulario para registrar visitas a eventos"""
    
    class Meta:
        model = VisitaEvento
        fields = ['nombre_cliente', 'cedula_cliente', 'telefono_cliente', 'email_cliente', 'observaciones']
        widgets = {
            'nombre_cliente': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg',
                'placeholder': 'Nombre completo del cliente',
                'required': True
            }),
            'cedula_cliente': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg',
                'placeholder': 'Número de cédula',
                'required': True,
                'pattern': '[0-9]+',
                'title': 'Solo números'
            }),
            'telefono_cliente': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg',
                'placeholder': 'Teléfono de contacto',
                'required': True,
                'pattern': '[0-9+\\-\\s()]+',
                'title': 'Formato: +593 9XXXXXXXX'
            }),
            'email_cliente': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg',
                'placeholder': 'Correo electrónico (opcional)'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Observaciones adicionales (opcional)'
            }),
        }
        labels = {
            'nombre_cliente': 'Nombre Completo',
            'cedula_cliente': 'Número de Cédula',
            'telefono_cliente': 'Teléfono',
            'email_cliente': 'Email',
            'observaciones': 'Observaciones',
        }
    
    def clean_cedula_cliente(self):
        cedula = self.cleaned_data.get('cedula_cliente')
        if cedula:
            # Limpiar espacios y caracteres no numéricos
            cedula = ''.join(filter(str.isdigit, cedula))
            
            # Validar longitud (cédula ecuatoriana: 10 dígitos)
            if len(cedula) != 10:
                raise forms.ValidationError('La cédula debe tener 10 dígitos.')
            
            # Validación básica de cédula ecuatoriana
            if not self.validar_cedula_ecuatoriana(cedula):
                raise forms.ValidationError('Número de cédula no válido.')
        
        return cedula
    
    def clean_telefono_cliente(self):
        telefono = self.cleaned_data.get('telefono_cliente')
        if telefono:
            # Limpiar formato
            telefono_limpio = ''.join(filter(str.isdigit, telefono))
            
            # Validar longitud mínima
            if len(telefono_limpio) < 7:
                raise forms.ValidationError('Número de teléfono muy corto.')
        
        return telefono
    
    def validar_cedula_ecuatoriana(self, cedula):
        """Validación básica de cédula ecuatoriana"""
        try:
            # Los dos primeros dígitos no pueden ser mayores a 24
            provincia = int(cedula[:2])
            if provincia < 1 or provincia > 24:
                return False
            
            # Algoritmo de validación del último dígito
            coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            suma = 0
            
            for i in range(9):
                digito = int(cedula[i])
                producto = digito * coeficientes[i]
                if producto > 9:
                    producto -= 9
                suma += producto
            
            digito_verificador = (10 - (suma % 10)) % 10
            return digito_verificador == int(cedula[9])
        
        except (ValueError, IndexError):
            return False


class InvitacionQRForm(forms.ModelForm):
    """Formulario para configurar invitaciones QR"""
    
    class Meta:
        model = InvitacionQR
        fields = ['usos_maximos', 'fecha_expiracion', 'activa']
        widgets = {
            'usos_maximos': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '1',
                'value': '999999'
            }),
            'fecha_expiracion': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'usos_maximos': 'Usos Máximos',
            'fecha_expiracion': 'Fecha de Expiración',
            'activa': 'Invitación Activa',
        }
    
    def clean_fecha_expiracion(self):
        fecha_expiracion = self.cleaned_data.get('fecha_expiracion')
        
        if fecha_expiracion and fecha_expiracion < timezone.now():
            raise forms.ValidationError('La fecha de expiración no puede ser en el pasado.')
        
        return fecha_expiracion


class EventoFilterForm(forms.Form):
    """Formulario de filtros para eventos"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Buscar por nombre, descripción o ubicación...'
        })
    )
    
    activo = forms.ChoiceField(
        choices=[
            ('', 'Todos los estados'),
            ('true', 'Activos'),
            ('false', 'Inactivos'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )