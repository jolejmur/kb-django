# apps/accounts/models.py - REEMPLAZAR COMPLETAMENTE

from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.core.exceptions import ValidationError


class MenuCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-folder')
    color = models.CharField(max_length=20, default='blue')
    order = models.IntegerField(default=0)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Categoría del Menú'
        verbose_name_plural = 'Categorías del Menú'

    def __str__(self):
        return self.name

    def get_modules(self):
        """Obtiene todos los módulos (grupos) que pertenecen a esta categoría"""
        return Group.objects.filter(navigation__category=self)

    def can_be_deleted(self):
        """Verifica si la categoría puede ser eliminada"""
        # No se puede eliminar si tiene módulos asignados
        return not self.get_modules().exists()

    def delete(self, *args, **kwargs):
        """Override delete para validar antes de eliminar"""
        if not self.can_be_deleted():
            raise ValidationError(
                f'No se puede eliminar la categoría "{self.name}" porque tiene módulos asignados.'
            )
        super().delete(*args, **kwargs)


class Navigation(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, unique=True)
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200)
    icon = models.CharField(max_length=50, default='fas fa-link')
    order = models.IntegerField(default=0)
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='navigations')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__order', 'order', 'name']
        verbose_name = 'Elemento de Navegación'
        verbose_name_plural = 'Elementos de Navegación'

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    groups = models.ManyToManyField(Group, blank=True, related_name='roles')
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)  # Nuevo campo para roles del sistema
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name

    def can_be_edited(self):
        """Verifica si el rol puede ser editado"""
        # Los roles del sistema no se pueden editar completamente
        return not self.is_system

    def can_be_deleted(self):
        """Verifica si el rol puede ser eliminado"""
        # No se puede eliminar si:
        # 1. Es un rol del sistema
        # 2. Tiene usuarios asignados
        if self.is_system:
            return False
        return not self.users.exists()

    def delete(self, *args, **kwargs):
        """Override delete para validar antes de eliminar"""
        if not self.can_be_deleted():
            if self.is_system:
                raise ValidationError(
                    f'No se puede eliminar el rol "{self.name}" porque es un rol del sistema.'
                )
            else:
                raise ValidationError(
                    f'No se puede eliminar el rol "{self.name}" porque tiene usuarios asignados.'
                )
        super().delete(*args, **kwargs)


# Extender el modelo Group con métodos adicionales
def group_can_be_deleted(self):
    """Verifica si el grupo puede ser eliminado"""
    # No se puede eliminar si está asignado a algún rol
    return not self.roles.exists()


def group_delete_override(self, *args, **kwargs):
    """Override delete para validar antes de eliminar"""
    if not self.can_be_deleted():
        raise ValidationError(
            f'No se puede eliminar el módulo "{self.name}" porque está asignado a uno o más roles.'
        )
    super(Group, self).delete(*args, **kwargs)


# Agregar métodos al modelo Group
Group.add_to_class('can_be_deleted', group_can_be_deleted)
Group.add_to_class('delete', group_delete_override)


class User(AbstractUser):
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_user_groups(self):
        """Obtiene los grupos/módulos del usuario a través de su rol"""
        if self.role:
            return self.role.groups.all()
        return Group.objects.none()

    def has_module_access(self, group_name):
        """Verifica si el usuario tiene acceso a un módulo específico"""
        return self.get_user_groups().filter(name=group_name).exists()

    def get_permissions(self):
        """Obtiene todos los permisos del usuario a través de su rol"""
        if not self.role:
            return set()

        permissions = set()
        for group in self.role.groups.all():
            for permission in group.permissions.all():
                permissions.add(permission)

        return permissions

    def get_navigation_items(self):
        """Obtiene elementos de navegación del usuario"""
        if not self.role:
            return []

        navigation_items = []
        for group in self.role.groups.all():
            try:
                nav_item = group.navigation
                if nav_item.is_active:
                    navigation_items.append(nav_item)
            except Navigation.DoesNotExist:
                continue

        # Ordenar por categoría y orden
        return sorted(navigation_items, key=lambda x: (x.category.order, x.order))

    def get_navigation_by_categories(self):
        """Obtiene elementos de navegación organizados por categorías"""
        navigation_items = self.get_navigation_items()

        # Organizar por categorías
        categories_dict = {}
        for nav_item in navigation_items:
            category_name = nav_item.category.name
            if category_name not in categories_dict:
                categories_dict[category_name] = {
                    'category': nav_item.category,
                    'items': []
                }
            categories_dict[category_name]['items'].append(nav_item)

        # Ordenar categorías por su campo order
        ordered_categories = dict(sorted(
            categories_dict.items(),
            key=lambda x: x[1]['category'].order
        ))

        return ordered_categories