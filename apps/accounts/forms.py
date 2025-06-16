from django import forms
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from .models import Navigation, Role

User = get_user_model()


class ModuleForm(forms.ModelForm):
    """
    Formulario para crear/editar MÓDULOS.
    Un módulo agrupa permisos de una área específica del sistema.
    Internamente usa Django Groups.
    """

    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Permisos del Módulo",
        help_text="Selecciona qué acciones permite este módulo del sistema"
    )

    # Campos para navegación
    nav_name = forms.CharField(
        max_length=100,
        required=False,
        label="Nombre en el Menú",
        help_text="Cómo aparecerá en el menú lateral (opcional)",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Ej: Gestión de Clientes'
        })
    )

    nav_url = forms.CharField(
        max_length=200,
        required=False,
        label="Enlace del Menú",
        help_text="Dirección web del módulo (opcional)",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Ej: /customers/'
        })
    )

    nav_icon = forms.CharField(
        max_length=50,
        required=False,
        label="Ícono del Menú",
        help_text="Ícono que aparecerá en el menú (FontAwesome)",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Ej: fas fa-users'
        })
    )

    nav_order = forms.IntegerField(
        initial=0,
        required=False,
        label="Orden en el Menú",
        help_text="Posición en el menú (número menor = más arriba)",
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'min': '0'
        })
    )

    class Meta:
        model = Group
        fields = ['name']
        labels = {
            'name': 'Nombre del Módulo'
        }
        help_texts = {
            'name': 'Nombre del área del sistema (ej: "Ventas", "Clientes", "Reportes")'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Ventas'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organize_permissions()
        if self.instance.pk:
            self.load_navigation_data()

    def organize_permissions(self):
        """Organiza los permisos por aplicación de forma comprensible"""
        all_permissions = Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'content_type__model', 'codename'
        )

        relevant_permissions = []
        for perm in all_permissions:
            app_label = perm.content_type.app_label
            model_name = perm.content_type.model
            codename = perm.codename

            if not self._should_exclude_permission(app_label, model_name, codename):
                relevant_permissions.append(perm)

        self.permissions_by_app = {}
        app_friendly_names = {
            'auth': 'Gestión de Usuarios',
            'accounts': 'Roles y Navegación',
            'core': 'Configuración del Sistema',
            'customers': 'Gestión de Clientes',
            'sales': 'Gestión de Ventas',
            'products': 'Gestión de Productos',
            'reports': 'Reportes y Análisis',
        }

        for perm in relevant_permissions:
            app_label = perm.content_type.app_label
            friendly_name = app_friendly_names.get(app_label, app_label.title())

            if friendly_name not in self.permissions_by_app:
                self.permissions_by_app[friendly_name] = []
            self.permissions_by_app[friendly_name].append(perm)

        self.fields['permissions'].queryset = Permission.objects.filter(
            id__in=[p.id for p in relevant_permissions]
        )

    def _should_exclude_permission(self, app_label, model_name, codename):
        """Excluye permisos internos que no son relevantes para usuarios finales"""
        excluded_apps = ['contenttypes', 'sessions', 'admin']
        if app_label in excluded_apps:
            return True

        excluded_permissions = [
            'auth.add_permission', 'auth.change_permission',
            'auth.delete_permission', 'auth.view_permission'
        ]

        full_codename = f"{app_label}.{codename}"
        if full_codename in excluded_permissions:
            return True

        return False

    def load_navigation_data(self):
        """Carga los datos de navegación si el módulo ya existe"""
        try:
            navigation = self.instance.navigation
            self.fields['nav_name'].initial = navigation.name
            self.fields['nav_url'].initial = navigation.url
            self.fields['nav_icon'].initial = navigation.icon
            self.fields['nav_order'].initial = navigation.order
        except Navigation.DoesNotExist:
            pass

    def save(self, commit=True):
        """Guarda el módulo y su configuración de navegación"""
        group = super().save(commit=commit)

        if commit:
            group.permissions.set(self.cleaned_data['permissions'])

            nav_name = self.cleaned_data.get('nav_name')
            if nav_name:
                navigation, created = Navigation.objects.get_or_create(
                    group=group,
                    defaults={
                        'name': nav_name,
                        'url': self.cleaned_data.get('nav_url', '#'),
                        'icon': self.cleaned_data.get('nav_icon', ''),
                        'order': self.cleaned_data.get('nav_order', 0),
                    }
                )

                if not created:
                    navigation.name = nav_name
                    navigation.url = self.cleaned_data.get('nav_url', '#')
                    navigation.icon = self.cleaned_data.get('nav_icon', '')
                    navigation.order = self.cleaned_data.get('nav_order', 0)
                    navigation.save()

        return group


class RoleForm(forms.ModelForm):
    """
    Formulario para crear/editar ROLES.
    Un rol combina varios módulos para crear un puesto específico.
    """

    modules = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Módulos Incluidos",
        help_text="Selecciona qué módulos del sistema tendrá este rol"
    )

    class Meta:
        model = Role
        fields = ['name', 'description']
        labels = {
            'name': 'Nombre del Rol',
            'description': 'Descripción del Rol'
        }
        help_texts = {
            'name': 'Nombre del puesto de trabajo (ej: "Vendedor", "Supervisor")',
            'description': 'Descripción de las responsabilidades de este rol'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Vendedor Senior'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Ej: Vendedor con experiencia que puede gestionar clientes premium'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modules'].queryset = Group.objects.all().order_by('name')
        if self.instance.pk:
            self.fields['modules'].initial = self.instance.groups.all()

    def save(self, commit=True):
        """Guarda el rol y asigna los módulos seleccionados"""
        role = super().save(commit=commit)
        if commit:
            role.groups.set(self.cleaned_data['modules'])
        return role


class UserForm(forms.ModelForm):
    """
    Formulario simple para gestionar usuarios y asignar roles.
    """

    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        empty_label="Sin rol asignado",
        label="Rol del Usuario",
        help_text="Selecciona el rol que tendrá este usuario",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'is_active', 'role']
        labels = {
            'username': 'Nombre de Usuario',
            'email': 'Correo Electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'phone_number': 'Teléfono',
            'is_active': 'Usuario Activo',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: juan.perez'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: juan@empresa.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Juan'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: Pérez'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Ej: +591 12345678'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }


class UserCreateForm(UserForm):
    """
    Formulario para crear usuarios con campo de contraseña.
    """

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Contraseña segura'
        })
    )

    password2 = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Confirma la contraseña'
        })
    )

    class Meta(UserForm.Meta):
        fields = UserForm.Meta.fields + ['password1', 'password2']

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user