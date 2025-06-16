from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class User(AbstractUser):
    """
    Modelo de usuario extendido que hereda de AbstractUser de Django.
    Los permisos se heredan a través del rol, no directamente de grupos.
    """
    # Campos adicionales que podrían ser útiles en un CRM
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # Relación con el modelo Role (un usuario tiene un rol)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    def get_permissions(self):
        """
        Obtiene todos los permisos del usuario a través de su rol.
        Ya no accede directamente a los grupos del usuario.
        """
        if not self.role:
            return set()

        permissions = set()
        for group in self.role.groups.all():
            permissions.update(group.permissions.all())
        return permissions

    def has_perm(self, perm, obj=None):
        """
        Sobreescribimos el método has_perm para usar los permisos del rol
        """
        if self.is_superuser:
            return True

        if not self.role:
            return False

        # Convertimos el perm a formato 'app_label.codename'
        if isinstance(perm, str):
            if '.' not in perm:
                return False
            app_label, codename = perm.split('.')
        else:
            app_label, codename = perm.split('.')

        # Verificamos si el usuario tiene el permiso a través de su rol
        return self.get_permissions().filter(
            content_type__app_label=app_label,
            codename=codename
        ).exists()

    def get_navigation_items(self):
        """
        Obtiene todos los elementos de navegación a los que el usuario tiene acceso
        a través de su rol y los grupos asociados.
        """
        if not self.role:
            return []

        navigation_items = []
        for group in self.role.groups.all():
            if hasattr(group, 'navigation') and group.navigation:
                navigation_items.append(group.navigation)

        # Ordenar por el campo 'order'
        return sorted(navigation_items, key=lambda x: x.order)

    def get_navigation_by_categories(self):
        """
        Obtiene elementos de navegación organizados por categorías para el superadmin
        """
        if not (self.is_superuser or self.is_staff):
            # Para usuarios normales, usar el método original
            return self.get_navigation_items_original()

        # Para superadmin: mostrar todas las categorías del sistema
        categories = {}

        # Obtener todas las categorías activas
        for category in MenuCategory.objects.filter(is_active=True).order_by('order'):
            modules = category.get_modules()
            if modules.exists():
                categories[category.name] = {
                    'category': category,
                    'items': [group.navigation for group in modules if hasattr(group, 'navigation')]
                }

        # Módulos sin categoría
        uncategorized_modules = Group.objects.filter(
            navigation__isnull=False,
            navigation__category__isnull=True
        )
        if uncategorized_modules.exists():
            categories['Sin Categoría'] = {
                'category': None,
                'items': [group.navigation for group in uncategorized_modules]
            }

        return categories

    def get_navigation_items_original(self):
        """
        Método original para usuarios con roles específicos
        """
        if not self.role:
            return []

        navigation_items = []
        for group in self.role.groups.all():
            if hasattr(group, 'navigation') and group.navigation:
                navigation_items.append(group.navigation)

        return sorted(navigation_items, key=lambda x: x.order)


class Role(models.Model):
    """
    Modelo para representar roles de usuario en el sistema.
    Un rol puede tener muchos grupos (M:N con auth.Group de Django).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Relación muchos a muchos con auth.Group de Django
    groups = models.ManyToManyField('auth.Group', related_name='roles')

    def __str__(self):
        return self.name

    def get_permissions(self):
        """
        Obtiene todos los permisos asociados a este rol a través de sus grupos
        """
        permissions = set()
        for group in self.groups.all():
            permissions.update(group.permissions.all())
        return permissions


class MenuCategory(models.Model):
    """
    Categorías para organizar los módulos en el sidebar dinámico.
    Ejemplo: "Ventas", "Administración", "Reportes"
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Categoría")
    description = models.TextField(blank=True, verbose_name="Descripción")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Ícono de la Categoría")
    color = models.CharField(
        max_length=20,
        default='blue',
        choices=[
            ('blue', 'Azul'),
            ('red', 'Rojo'),
            ('green', 'Verde'),
            ('purple', 'Morado'),
            ('yellow', 'Amarillo'),
            ('orange', 'Naranja'),
            ('pink', 'Rosa'),
            ('gray', 'Gris'),
        ],
        verbose_name="Color de la Categoría"
    )
    order = models.IntegerField(default=0, verbose_name="Orden de Aparición")
    is_active = models.BooleanField(default=True, verbose_name="Categoría Activa")
    is_system = models.BooleanField(default=False, verbose_name="Categoría del Sistema")

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Categoría de Menú"
        verbose_name_plural = "Categorías de Menú"

    def __str__(self):
        return self.name

    def get_modules(self):
        """Obtiene todos los módulos (Groups) de esta categoría"""
        return Group.objects.filter(navigation__category=self, navigation__isnull=False).order_by('navigation__order')


class Navigation(models.Model):
    """
    Modelo para representar elementos de navegación en el sidebar.
    Cada grupo tiene una sola ruta de navegación (1:1 con auth.Group).
    """
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200)
    icon = models.CharField(max_length=50, blank=True)  # Nombre de clase de icono (FontAwesome, etc.)
    order = models.IntegerField(default=0)

    # Auto-referencia para crear una estructura jerárquica
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    # Relación uno a uno con auth.Group (un grupo tiene una sola navegación)
    group = models.OneToOneField('auth.Group', on_delete=models.CASCADE, related_name='navigation', null=True,
                                 blank=True)

    # NUEVO: Relación con MenuCategory
    category = models.ForeignKey(
        'MenuCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='navigation_items',
        verbose_name="Categoría"
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    @property
    def is_parent(self):
        """Verifica si este elemento tiene hijos"""
        return self.children.exists()

    @property
    def get_children(self):
        """Obtiene los hijos ordenados por el campo 'order'"""
        return self.children.all().order_by('order')