from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileEditForm(forms.ModelForm):
    """
    Form for editing user profile information.
    Only allows editing of safe, user-modifiable fields.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telefono', 'foto_perfil', 'domicilio', 'latitud', 'longitud']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Ingresa tu nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Ingresa tu apellido'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Ingresa tu email'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Ingresa tu número de teléfono'
            }),
            'foto_perfil': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'accept': 'image/*'
            }),
            'domicilio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Dirección completa (calle, número, zona, ciudad)',
                'rows': 3
            }),
            'latitud': forms.NumberInput(attrs={
                'class': 'w-full px-2 py-1 border border-gray-300 rounded text-sm',
                'step': '0.0000001',
                'readonly': True
            }),
            'longitud': forms.NumberInput(attrs={
                'class': 'w-full px-2 py-1 border border-gray-300 rounded text-sm',
                'step': '0.0000001',
                'readonly': True
            })
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'foto_perfil': 'Foto de Perfil',
            'domicilio': 'Dirección',
            'latitud': 'Latitud',
            'longitud': 'Longitud'
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with Tailwind styling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply Tailwind classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            })

        # Update labels and help texts
        self.fields['old_password'].label = 'Current Password'
        self.fields['new_password1'].label = 'New Password'
        self.fields['new_password2'].label = 'Confirm New Password'

        # Add placeholders
        self.fields['old_password'].widget.attrs['placeholder'] = 'Enter your current password'
        self.fields['new_password1'].widget.attrs['placeholder'] = 'Enter your new password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm your new password'