# apps/whatsapp_business/forms.py
from django import forms
from .models import WhatsAppConfig


class WhatsAppConfigForm(forms.ModelForm):
    """
    Formulario para configurar WhatsApp Business
    """
    
    class Meta:
        model = WhatsAppConfig
        fields = [
            'phone_number_id',
            'business_account_id',
            'whatsapp_business_account_id',
            'access_token',
            'webhook_verify_token',
            'webhook_url',
            'is_active'
        ]
        widgets = {
            'phone_number_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1234567890123456'
            }),
            'business_account_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1234567890123456'
            }),
            'whatsapp_business_account_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1234567890123456'
            }),
            'access_token': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Token de acceso de WhatsApp Business API (Meta Token)',
                'style': 'font-family: monospace; font-size: 0.9rem;'
            }),
            'webhook_verify_token': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Token de verificación del webhook'
            }),
            'webhook_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://tu-dominio.com/webhook/whatsapp'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'phone_number_id': 'ID del Número de Teléfono',
            'business_account_id': 'ID de la Cuenta Comercial',
            'whatsapp_business_account_id': 'ID de la Cuenta de WhatsApp Business',
            'access_token': 'Token de Acceso',
            'webhook_verify_token': 'Token de Verificación del Webhook',
            'webhook_url': 'URL del Webhook',
            'is_active': 'Configuración Activa'
        }
        help_texts = {
            'phone_number_id': 'ID del número de teléfono de WhatsApp Business obtenido de Meta Business',
            'business_account_id': 'ID de la cuenta comercial de WhatsApp Business',
            'whatsapp_business_account_id': 'ID de la cuenta de WhatsApp Business (diferente del Business Account ID)',
            'access_token': 'Token de acceso permanente para la API de WhatsApp Business',
            'webhook_verify_token': 'Token secreto para verificar la autenticidad del webhook',
            'webhook_url': 'URL donde Meta enviará los webhooks de WhatsApp',
            'is_active': 'Marcar como activa para usar esta configuración'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que todos los campos sean requeridos excepto is_active y whatsapp_business_account_id
        for field_name, field in self.fields.items():
            if field_name not in ['is_active', 'whatsapp_business_account_id']:
                field.required = True

    def clean_access_token(self):
        """Validar que el token de acceso tenga el formato correcto"""
        token = self.cleaned_data.get('access_token')
        if token:
            # Validación básica del token
            if len(token) < 50:
                raise forms.ValidationError('El token de acceso parece ser muy corto')
            if not token.startswith('EAA'):
                raise forms.ValidationError('El token de acceso debe comenzar con "EAA"')
        return token

    def clean_phone_number_id(self):
        """Validar que el phone_number_id tenga el formato correcto"""
        phone_id = self.cleaned_data.get('phone_number_id')
        if phone_id:
            if not phone_id.isdigit():
                raise forms.ValidationError('El ID del número de teléfono debe contener solo números')
            if len(phone_id) < 10:
                raise forms.ValidationError('El ID del número de teléfono es muy corto')
        return phone_id

    def clean_business_account_id(self):
        """Validar que el business_account_id tenga el formato correcto"""
        account_id = self.cleaned_data.get('business_account_id')
        if account_id:
            if not account_id.isdigit():
                raise forms.ValidationError('El ID de la cuenta comercial debe contener solo números')
            if len(account_id) < 10:
                raise forms.ValidationError('El ID de la cuenta comercial es muy corto')
        return account_id
    
    def clean_whatsapp_business_account_id(self):
        """Validar que el whatsapp_business_account_id tenga el formato correcto"""
        account_id = self.cleaned_data.get('whatsapp_business_account_id')
        if account_id:
            if not account_id.isdigit():
                raise forms.ValidationError('El ID de la cuenta de WhatsApp Business debe contener solo números')
            if len(account_id) < 10:
                raise forms.ValidationError('El ID de la cuenta de WhatsApp Business es muy corto')
        return account_id

    def clean_webhook_url(self):
        """Validar que la URL del webhook sea HTTPS"""
        url = self.cleaned_data.get('webhook_url')
        if url:
            if not url.startswith('https://'):
                raise forms.ValidationError('La URL del webhook debe usar HTTPS')
        return url

    def clean(self):
        """Validaciones generales del formulario"""
        cleaned_data = super().clean()
        is_active = cleaned_data.get('is_active')
        
        # Si se marca como activa, verificar que no haya otra configuración activa
        if is_active:
            existing_active = WhatsAppConfig.objects.filter(is_active=True)
            if self.instance and self.instance.pk:
                existing_active = existing_active.exclude(pk=self.instance.pk)
            
            if existing_active.exists():
                raise forms.ValidationError(
                    'Ya existe una configuración activa. Solo puede haber una configuración activa a la vez.'
                )
        
        return cleaned_data

    def save(self, commit=True):
        """Guardar la configuración"""
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
        
        return instance