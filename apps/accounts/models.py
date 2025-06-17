# apps/accounts/models.py - REEMPLAZAR COMPLETAMENTE

from django.contrib.auth.models import AbstractUser, Group
from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


class User(AbstractUser):
    # AÑADIR related_name='users' para que Role.users funcione
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'  # ← ESTO ES LO QUE FALTABA
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