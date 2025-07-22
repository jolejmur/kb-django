from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, MenuCategory, Navigation


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuración del admin para el modelo User personalizado
    """
    # Campos que se mostrarán en la lista
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'role', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    # Configuración de los fieldsets para el formulario de edición
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('role',),
        }),
    )

    # Campos para el formulario de creación
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('email', 'first_name', 'last_name', 'role'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Role
    """
    list_display = ('name', 'description', 'get_groups_count', 'get_users_count')
    search_fields = ('name', 'description')
    filter_horizontal = ('groups',)

    def get_groups_count(self, obj):
        return obj.groups.count()

    get_groups_count.short_description = 'Módulos'

    def get_users_count(self, obj):
        return obj.users.count()

    get_users_count.short_description = 'Usuarios'


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo MenuCategory
    """
    list_display = ('name', 'description', 'color', 'order', 'is_active', 'is_system')
    list_filter = ('is_active', 'is_system', 'color')
    search_fields = ('name', 'description')
    ordering = ('order', 'name')


@admin.register(Navigation)
class NavigationAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Navigation
    """
    list_display = ('name', 'url', 'group', 'category', 'order', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'url')
    ordering = ('order', 'name')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'category')