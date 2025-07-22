# Detalle de Modelos para la Aplicación de Cuentas (accounts)

A continuación se presenta un detalle más específico de cómo implementar los modelos para el sistema de usuarios, roles, grupos y permisos en Django.

## Modelo de Usuario Extendido

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Modelo de usuario extendido que hereda de AbstractUser de Django.
    Mantiene toda la funcionalidad del usuario de Django mientras permite
    añadir campos y métodos adicionales.
    """
    # Campos adicionales que podrían ser útiles en un CRM
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Relación con el modelo Role (un usuario tiene un rol)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    
    def get_permissions(self):
        """
        Obtiene todos los permisos del usuario a través de su rol y los grupos asociados.
        """
        if not self.role:
            return set()
        
        permissions = set()
        for group in self.role.groups.all():
            for permission in group.permissions.all():
                permissions.add(permission)
        
        return permissions
    
    def get_navigation_items(self):
        """
        Obtiene todos los elementos de navegación a los que el usuario tiene acceso
        a través de su rol y los grupos asociados.
        """
        if not self.role:
            return []
        
        navigation_items = []
        for group in self.role.groups.all():
            for nav_item in group.navigation_items.all():
                navigation_items.append(nav_item)
        
        # Ordenar por el campo 'order'
        return sorted(navigation_items, key=lambda x: x.order)
```

## Modelo de Rol

```python
# apps/accounts/models.py (continuación)
class Role(models.Model):
    """
    Modelo para representar roles de usuario en el sistema.
    Un rol puede pertenecer a múltiples grupos.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Relación muchos a muchos con Group
    groups = models.ManyToManyField('Group', related_name='roles')
    
    def __str__(self):
        return self.name
```

## Modelo de Grupo

```python
# apps/accounts/models.py (continuación)
class Group(models.Model):
    """
    Modelo personalizado de Grupo que no utiliza el modelo Group de Django.
    Un grupo tiene múltiples permisos y elementos de navegación.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Relación muchos a muchos con Permission de Django
    permissions = models.ManyToManyField('auth.Permission', related_name='custom_groups')
    
    def __str__(self):
        return self.name
```

## Modelo de Navegación

```python
# apps/accounts/models.py (continuación)
class Navigation(models.Model):
    """
    Modelo para representar elementos de navegación en el sidebar.
    Cada elemento puede estar asociado a uno o más grupos.
    """
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=200)
    icon = models.CharField(max_length=50, blank=True)  # Nombre de clase de icono (FontAwesome, etc.)
    order = models.IntegerField(default=0)
    
    # Auto-referencia para crear una estructura jerárquica
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Relación muchos a muchos con Group
    groups = models.ManyToManyField(Group, related_name='navigation_items')
    
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
```

## Ejemplo de Uso en Vistas

```python
# apps/accounts/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard(request):
    """
    Vista de ejemplo que muestra cómo utilizar los métodos del modelo User
    para obtener elementos de navegación dinámicos.
    """
    user = request.user
    navigation_items = user.get_navigation_items()
    
    context = {
        'navigation_items': navigation_items,
    }
    
    return render(request, 'accounts/dashboard.html', context)
```

## Ejemplo de Plantilla con Sidebar Dinámico

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}CRM Django{% endblock %}</title>
    <!-- CSS y JS aquí -->
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h3>CRM Django</h3>
        </div>
        
        <ul class="sidebar-menu">
            {% for item in request.user.get_navigation_items %}
                {% if not item.parent %}  <!-- Solo elementos de nivel superior -->
                    <li class="sidebar-item {% if item.is_parent %}has-children{% endif %}">
                        <a href="{{ item.url }}">
                            {% if item.icon %}<i class="{{ item.icon }}"></i>{% endif %}
                            <span>{{ item.name }}</span>
                        </a>
                        
                        {% if item.is_parent %}
                            <ul class="sidebar-submenu">
                                {% for child in item.get_children %}
                                    <li>
                                        <a href="{{ child.url }}">
                                            {% if child.icon %}<i class="{{ child.icon }}"></i>{% endif %}
                                            <span>{{ child.name }}</span>
                                        </a>
                                    </li>
                                {% endfor %}
                            </ul>
                        {% endif %}
                    </li>
                {% endif %}
            {% endfor %}
        </ul>
    </div>
    
    <div class="main-content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

## Configuración en settings.py

```python
# config/settings/base.py

# ...

# Especificar el modelo de usuario personalizado
AUTH_USER_MODEL = 'accounts.User'

# Añadir las aplicaciones necesarias
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Aplicaciones de terceros
    'rest_framework',  # Para la API
    
    # Aplicaciones propias
    'apps.core',
    'apps.accounts',
    'apps.customers',
    # Otras aplicaciones...
]

# ...
```

Este diseño proporciona una implementación detallada de los modelos necesarios para el sistema de usuarios, roles, grupos y permisos con navegación dinámica. La estructura permite una gran flexibilidad mientras aprovecha el sistema de autenticación y permisos de Django.