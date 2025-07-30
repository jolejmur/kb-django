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
    
    # Información personal adicional
    fecha_nacimiento = models.DateField(
        verbose_name='Fecha de Nacimiento',
        null=True,
        blank=True,
        help_text='Fecha de nacimiento del usuario'
    )
    
    cedula = models.CharField(
        max_length=20,
        verbose_name='Cédula de Identidad',
        null=True,
        blank=True,
        unique=True,
        help_text='Número de cédula de identidad o documento de identificación'
    )
    
    domicilio = models.CharField(
        max_length=255,
        verbose_name='Domicilio',
        null=True,
        blank=True,
        help_text='Dirección completa del domicilio'
    )
    
    telefono = models.CharField(
        max_length=20,
        verbose_name='Teléfono',
        null=True,
        blank=True,
        help_text='Número de teléfono de contacto'
    )
    
    # Coordenadas geográficas
    latitud = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name='Latitud',
        null=True,
        blank=True,
        help_text='Latitud de la ubicación del domicilio (-90 a +90)'
    )
    
    longitud = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name='Longitud',
        null=True,
        blank=True,
        help_text='Longitud de la ubicación del domicilio (-180 a +180)'
    )
    
    # Campos existentes
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
    
    def has_perm(self, perm, obj=None):
        """
        Override del método has_perm para incluir permisos de roles
        """
        # Primero verificar permisos estándar de Django
        if super().has_perm(perm, obj):
            return True
        
        # Si no tiene permisos directos, verificar a través del rol
        if not self.role:
            return False
            
        # Verificar si tiene el permiso a través de su rol
        for group in self.role.groups.all():
            if group.permissions.filter(
                content_type__app_label=perm.split('.')[0],
                codename=perm.split('.')[1]
            ).exists():
                return True
                
        return False
    
    def has_perms(self, perm_list, obj=None):
        """
        Override del método has_perms para incluir permisos de roles
        """
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

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
    
    def get_coordenadas(self):
        """Obtiene las coordenadas geográficas como tupla"""
        if self.latitud and self.longitud:
            return (float(self.latitud), float(self.longitud))
        return None
    
    def set_coordenadas(self, latitud, longitud):
        """Establece las coordenadas geográficas"""
        self.latitud = latitud
        self.longitud = longitud
    
    def has_coordenadas(self):
        """Verifica si el usuario tiene coordenadas geográficas"""
        return self.latitud is not None and self.longitud is not None
    
    def get_edad(self):
        """Calcula la edad del usuario basada en su fecha de nacimiento"""
        if self.fecha_nacimiento:
            from datetime import date
            today = date.today()
            return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        return None
    
    def get_info_completa(self):
        """Obtiene información completa del usuario"""
        return {
            'nombre_completo': self.get_full_name() or self.username,
            'email': self.email,
            'cedula': self.cedula,
            'fecha_nacimiento': self.fecha_nacimiento,
            'edad': self.get_edad(),
            'domicilio': self.domicilio,
            'coordenadas': self.get_coordenadas(),
            'fecha_creacion': self.created_at,
            'activo': self.is_active,
            'rol': self.role.name if self.role else None
        }
    
    # ============================================================
    # MÉTODOS PARA JERARQUÍA DE VENTAS (INCLUYENDO SUPERVISIÓN DIRECTA)
    # ============================================================
    
    def get_supervisores_directos(self, equipo_venta=None):
        """
        Obtiene supervisores directos (excepciones) de este usuario.
        Si no tiene supervisores directos, retorna supervisores de jerarquía normal.
        """
        from apps.sales_team_management.models import SupervisionDirecta
        
        # Filtro base
        filtros = {'subordinado': self, 'activo': True}
        if equipo_venta:
            filtros['equipo_venta'] = equipo_venta
        
        supervisores_directos = SupervisionDirecta.objects.filter(**filtros)
        
        if supervisores_directos.exists():
            # Tiene supervisores directos, retornarlos
            return [(sd.supervisor, f'Supervisor Directo ({sd.get_tipo_supervision_display()})') 
                    for sd in supervisores_directos]
        else:
            # No tiene supervisores directos, usar jerarquía normal
            return self._get_supervisores_jerarquia_normal(equipo_venta)
    
    def get_subordinados_directos(self, equipo_venta=None):
        """
        Obtiene subordinados directos (excepciones) de este usuario.
        Además retorna subordinados de jerarquía normal.
        """
        from apps.sales_team_management.models import SupervisionDirecta
        
        subordinados = []
        
        # 1. Subordinados por supervisión directa
        filtros = {'supervisor': self, 'activo': True}
        if equipo_venta:
            filtros['equipo_venta'] = equipo_venta
        
        supervisiones_directas = SupervisionDirecta.objects.filter(**filtros)
        for sd in supervisiones_directas:
            subordinados.append((
                sd.subordinado, 
                f'Subordinado Directo ({sd.get_tipo_supervision_display()})'
            ))
        
        # 2. Subordinados por jerarquía normal
        subordinados.extend(self._get_subordinados_jerarquia_normal(equipo_venta))
        
        return subordinados
    
    def _get_supervisores_jerarquia_normal(self, equipo_venta=None):
        """Obtiene supervisores según jerarquía normal"""
        supervisores = []
        
        # Buscar en vendedores (supervisor = team leader)
        vendedores = self.vendedores.filter(activo=True)
        if equipo_venta:
            vendedores = vendedores.filter(
                team_leader__jefe_venta__gerente_equipo__equipo_venta=equipo_venta
            )
        
        for vendedor in vendedores:
            supervisores.append((vendedor.team_leader.usuario, 'Team Leader (Jerarquía Normal)'))
        
        # Buscar en team leaders (supervisor = jefe venta)
        team_leaders = self.team_leaders.filter(activo=True)
        if equipo_venta:
            team_leaders = team_leaders.filter(
                jefe_venta__gerente_equipo__equipo_venta=equipo_venta
            )
        
        for tl in team_leaders:
            supervisores.append((tl.jefe_venta.usuario, 'Jefe de Venta (Jerarquía Normal)'))
        
        # Buscar en jefes de venta (supervisor = gerente)
        jefes_venta = self.jefe_ventas.filter(activo=True)
        if equipo_venta:
            jefes_venta = jefes_venta.filter(
                gerente_equipo__equipo_venta=equipo_venta
            )
        
        for jefe in jefes_venta:
            supervisores.append((jefe.gerente_equipo.usuario, 'Gerente de Equipo (Jerarquía Normal)'))
        
        return supervisores
    
    def _get_subordinados_jerarquia_normal(self, equipo_venta=None):
        """Obtiene subordinados según jerarquía normal"""
        subordinados = []
        
        # Si es gerente (subordinados = jefes de venta)
        gerencias = self.gerente_equipos.filter(activo=True)
        if equipo_venta:
            gerencias = gerencias.filter(equipo_venta=equipo_venta)
        
        for gerencia in gerencias:
            for jefe in gerencia.jefeventas.filter(activo=True):
                subordinados.append((jefe.usuario, 'Jefe de Venta (Jerarquía Normal)'))
        
        # Si es jefe de venta (subordinados = team leaders)
        jefaturas = self.jefe_ventas.filter(activo=True)
        if equipo_venta:
            jefaturas = jefaturas.filter(gerente_equipo__equipo_venta=equipo_venta)
        
        for jefatura in jefaturas:
            for tl in jefatura.teamleaders.filter(activo=True):
                subordinados.append((tl.usuario, 'Team Leader (Jerarquía Normal)'))
        
        # Si es team leader (subordinados = vendedores)
        team_leaderships = self.team_leaders.filter(activo=True)
        if equipo_venta:
            team_leaderships = team_leaderships.filter(
                jefe_venta__gerente_equipo__equipo_venta=equipo_venta
            )
        
        for tl in team_leaderships:
            for vendedor in tl.vendedores.filter(activo=True):
                subordinados.append((vendedor.usuario, 'Vendedor (Jerarquía Normal)'))
        
        return subordinados
    
    def get_equipo_venta(self):
        """Obtiene el equipo de venta al que pertenece este usuario"""
        from apps.sales_team_management.models import EquipoVenta
        
        # Buscar en gerentes
        gerencia = self.gerente_equipos.filter(activo=True).first()
        if gerencia:
            return gerencia.equipo_venta
        
        # Buscar en jefes de venta
        jefatura = self.jefe_ventas.filter(activo=True).first()
        if jefatura:
            return jefatura.gerente_equipo.equipo_venta
        
        # Buscar en team leaders
        team_leadership = self.team_leaders.filter(activo=True).first()
        if team_leadership:
            return team_leadership.jefe_venta.gerente_equipo.equipo_venta
        
        # Buscar en vendedores
        venta = self.vendedores.filter(activo=True).first()
        if venta:
            return venta.team_leader.jefe_venta.gerente_equipo.equipo_venta
        
        return None
    
    def get_rol_en_equipo_venta(self, equipo_venta=None):
        """Obtiene el rol del usuario en el equipo de ventas"""
        if not equipo_venta:
            equipo_venta = self.get_equipo_venta()
        
        if not equipo_venta:
            return None
        
        # Verificar cada nivel de jerarquía
        if self.gerente_equipos.filter(equipo_venta=equipo_venta, activo=True).exists():
            return 'GERENTE_EQUIPO'
        
        if self.jefe_ventas.filter(
            gerente_equipo__equipo_venta=equipo_venta, 
            activo=True
        ).exists():
            return 'JEFE_VENTA'
        
        if self.team_leaders.filter(
            jefe_venta__gerente_equipo__equipo_venta=equipo_venta, 
            activo=True
        ).exists():
            return 'TEAM_LEADER'
        
        if self.vendedores.filter(
            team_leader__jefe_venta__gerente_equipo__equipo_venta=equipo_venta, 
            activo=True
        ).exists():
            return 'VENDEDOR'
        
        return None
    
    def tiene_supervision_directa_activa(self, como_supervisor=True, equipo_venta=None):
        """Verifica si el usuario tiene supervisión directa activa"""
        from apps.sales_team_management.models import SupervisionDirecta
        
        filtros = {'activo': True}
        if equipo_venta:
            filtros['equipo_venta'] = equipo_venta
        
        if como_supervisor:
            filtros['supervisor'] = self
        else:
            filtros['subordinado'] = self
        
        return SupervisionDirecta.objects.filter(**filtros).exists()