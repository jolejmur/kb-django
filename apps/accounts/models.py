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
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_user_groups(self):
        if self.role:
            return self.role.groups.all()
        return Group.objects.none()

    def has_module_access(self, group_name):
        return self.get_user_groups().filter(name=group_name).exists()