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

        # Si estamos editando un módulo existente, cargar los datos
        if self.instance.pk:
            self.load_existing_data()

    def organize_permissions(self):
        """Organiza los permisos por función específica y relevante"""
        all_permissions = Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'content_type__model', 'codename'
        )

        # Filtrar solo permisos relevantes
        relevant_permissions = []
        for perm in all_permissions:
            if not self._should_exclude_permission(perm):
                relevant_permissions.append(perm)

        # Organizar por áreas funcionales específicas
        self.permissions_by_app = {
            'Gestión de Módulos (Groups)': [],
            'Gestión de Permisos': [],
            'Gestión de Roles': [],
            'Gestión de Usuarios': [],
            'Categorías del Menú': [],
            'Elementos de Navegación': [],
            'Configuración del Sistema': [],
            'Otros Permisos': []
        }

        for perm in relevant_permissions:
            app_label = perm.content_type.app_label
            model_name = perm.content_type.model

            # Clasificar por tipo de modelo
            if model_name == 'group':
                self.permissions_by_app['Gestión de Módulos (Groups)'].append(perm)
            elif model_name == 'permission':
                self.permissions_by_app['Gestión de Permisos'].append(perm)
            elif model_name == 'role':
                self.permissions_by_app['Gestión de Roles'].append(perm)
            elif model_name == 'user':
                self.permissions_by_app['Gestión de Usuarios'].append(perm)
            elif model_name == 'menucategory':
                self.permissions_by_app['Categorías del Menú'].append(perm)
            elif model_name == 'navigation':
                self.permissions_by_app['Elementos de Navegación'].append(perm)
            elif model_name == 'coresettings':
                self.permissions_by_app['Configuración del Sistema'].append(perm)
            else:
                self.permissions_by_app['Otros Permisos'].append(perm)

        # Remover categorías vacías
        self.permissions_by_app = {
            k: v for k, v in self.permissions_by_app.items() if v
        }

        self.fields['permissions'].queryset = Permission.objects.filter(
            id__in=[p.id for p in relevant_permissions]
        )

    def _should_exclude_permission(self, permission):
        """Excluye permisos internos que no son relevantes para usuarios finales"""
        app_label = permission.content_type.app_label
        model_name = permission.content_type.model
        codename = permission.codename

        # Aplicaciones a excluir completamente
        excluded_apps = ['contenttypes', 'sessions', 'admin']
        if app_label in excluded_apps:
            return True

        # Permisos específicos a excluir
        excluded_permissions = [
            'auth.add_permission',
            'auth.change_permission',
            'auth.delete_permission'
        ]

        full_codename = f"{app_label}.{codename}"
        if full_codename in excluded_permissions:
            return True

        return False

    def load_existing_data(self):
        """Carga los datos existentes del módulo para edición"""
        try:
            # Cargar permisos actuales del grupo
            current_permissions = self.instance.permissions.all()
            self.fields['permissions'].initial = current_permissions

            # Cargar datos de navegación si existe
            navigation = self.instance.navigation
            self.fields['nav_name'].initial = navigation.name
            self.fields['nav_url'].initial = navigation.url
            self.fields['nav_icon'].initial = navigation.icon
            self.fields['nav_order'].initial = navigation.order

        except Navigation.DoesNotExist:
            # Si no hay navegación, los campos quedan vacíos
            pass
        except Exception as e:
            # En caso de cualquier otro error, continuar silenciosamente
            pass

    def clean(self):
        """Validación adicional del formulario"""
        cleaned_data = super().clean()
        nav_name = cleaned_data.get('nav_name')
        nav_url = cleaned_data.get('nav_url')

        # Si se proporciona nombre de navegación, URL es requerida
        if nav_name and not nav_url:
            raise forms.ValidationError({
                'nav_url': 'La URL es requerida si proporcionas un nombre para el menú.'
            })

        return cleaned_data

    def save(self, commit=True):
        """Guarda el módulo y su configuración de navegación"""
        group = super().save(commit=commit)

        if commit:
            # Guardar permisos seleccionados
            group.permissions.set(self.cleaned_data['permissions'])

            # Manejar configuración de navegación
            nav_name = self.cleaned_data.get('nav_name')

            if nav_name:
                # Crear o actualizar navegación
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
                    # Actualizar navegación existente
                    navigation.name = nav_name
                    navigation.url = self.cleaned_data.get('nav_url', '#')
                    navigation.icon = self.cleaned_data.get('nav_icon', '')
                    navigation.order = self.cleaned_data.get('nav_order', 0)
                    navigation.save()
            else:
                # Si no hay nombre de navegación, eliminar navegación existente
                try:
                    if hasattr(group, 'navigation'):
                        group.navigation.delete()
                except Navigation.DoesNotExist:
                    pass

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

        # Si estamos editando un rol existente, cargar módulos actuales
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
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'role']
        labels = {
            'username': 'Nombre de Usuario',
            'email': 'Correo Electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
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