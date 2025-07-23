# apps/sales/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class EquipoVenta(models.Model):
    """
    Modelo para representar equipos de venta.
    Cada equipo tiene una estructura jerárquica de roles.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Equipo de Venta'
        verbose_name_plural = 'Equipos de Venta'
        ordering = ['nombre']

    def clean(self):
        """Validaciones personalizadas del modelo"""
        from django.core.exceptions import ValidationError
        
        # Limpiar espacios del principio y final del nombre
        if self.nombre:
            self.nombre = self.nombre.strip()
            
        # Validar que el nombre no esté vacío después de limpiar espacios
        if not self.nombre:
            raise ValidationError({'nombre': 'El nombre no puede estar vacío o contener solo espacios.'})
            
        # Validar unicidad considerando espacios
        existing_equipo = EquipoVenta.objects.filter(
            nombre__iexact=self.nombre.strip()
        ).exclude(pk=self.pk)
        
        if existing_equipo.exists():
            raise ValidationError({
                'nombre': f'Ya existe un equipo con el nombre "{self.nombre}". Los nombres deben ser únicos.'
            })

    def save(self, *args, **kwargs):
        """Sobrescribir save para limpiar el nombre antes de guardar"""
        # Limpiar espacios antes de guardar
        if self.nombre:
            self.nombre = self.nombre.strip()
        
        # Ejecutar validaciones
        self.full_clean()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    @property
    def gerentes_equipo(self):
        """Obtiene los gerentes de este equipo"""
        return self.gerenteequipo_set.filter(activo=True)

    @property
    def total_vendedores(self):
        """Cuenta el total de vendedores activos en el equipo"""
        count = 0
        for gerente in self.gerentes_equipo:
            for jefe in gerente.jefeventas.filter(activo=True):
                for team_leader in jefe.teamleaders.filter(activo=True):
                    count += team_leader.vendedores.filter(activo=True).count()
        return count

    def can_be_deleted(self):
        """Verifica si el equipo puede ser eliminado"""
        # No se puede eliminar si tiene proyectos asignados
        if self.proyectos.exists():
            return False
        
        # Verificar si tiene gerentes activos
        gerentes_activos = self.gerenteequipo_set.filter(activo=True)
        if gerentes_activos.exists():
            return False
        
        # Verificar si tiene jefes de venta activos
        for gerente in self.gerenteequipo_set.all():
            if gerente.jefeventas.filter(activo=True).exists():
                return False
            
            # Verificar si tiene team leaders activos
            for jefe in gerente.jefeventas.all():
                if jefe.teamleaders.filter(activo=True).exists():
                    return False
                
                # Verificar si tiene vendedores activos
                for team_leader in jefe.teamleaders.all():
                    if team_leader.vendedores.filter(activo=True).exists():
                        return False
        
        return True

    def get_deletion_blockers(self):
        """Obtiene una lista de elementos que impiden la eliminación del equipo"""
        blockers = []
        
        # Verificar proyectos asignados
        if self.proyectos.exists():
            blockers.append(f"{self.proyectos.count()} proyecto(s) asignado(s)")
        
        # Contar miembros activos por rol
        gerentes_count = self.gerenteequipo_set.filter(activo=True).count()
        if gerentes_count > 0:
            blockers.append(f"{gerentes_count} gerente(s) activo(s)")
        
        jefes_count = 0
        team_leaders_count = 0
        vendedores_count = 0
        
        for gerente in self.gerenteequipo_set.all():
            jefes_activos = gerente.jefeventas.filter(activo=True)
            jefes_count += jefes_activos.count()
            
            for jefe in jefes_activos:
                team_leaders_activos = jefe.teamleaders.filter(activo=True)
                team_leaders_count += team_leaders_activos.count()
                
                for team_leader in team_leaders_activos:
                    vendedores_count += team_leader.vendedores.filter(activo=True).count()
        
        if jefes_count > 0:
            blockers.append(f"{jefes_count} jefe(s) de venta activo(s)")
        if team_leaders_count > 0:
            blockers.append(f"{team_leaders_count} team leader(s) activo(s)")
        if vendedores_count > 0:
            blockers.append(f"{vendedores_count} vendedor(es) activo(s)")
        
        return blockers


# ============================================================
# ROLES ESPECÍFICOS DE VENTAS (JERARQUÍA)
# ============================================================

class GerenteEquipo(models.Model):
    """Gerente de Equipo de Ventas - Nivel más alto en la jerarquía de ventas"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gerente_equipos')
    equipo_venta = models.ForeignKey(EquipoVenta, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Gerente de Equipo'
        verbose_name_plural = 'Gerentes de Equipo'
        unique_together = ['usuario', 'equipo_venta']

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - {self.equipo_venta.nombre}"


class JefeVenta(models.Model):
    """Jefe de Venta - Reporta al Gerente de Equipo"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jefe_ventas')
    gerente_equipo = models.ForeignKey(GerenteEquipo, on_delete=models.CASCADE, related_name='jefeventas')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Jefe de Venta'
        verbose_name_plural = 'Jefes de Venta'

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - Jefe de Venta"


class TeamLeader(models.Model):
    """Team Leader - Reporta al Jefe de Venta"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_leaders')
    jefe_venta = models.ForeignKey(JefeVenta, on_delete=models.CASCADE, related_name='teamleaders')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Team Leader'
        verbose_name_plural = 'Team Leaders'

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - Team Leader"


class Vendedor(models.Model):
    """Vendedor - Reporta al Team Leader"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vendedores')
    team_leader = models.ForeignKey(TeamLeader, on_delete=models.CASCADE, related_name='vendedores')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - Vendedor"




# ============================================================
# SUPERVISIÓN DIRECTA (EXCEPCIONES A LA JERARQUÍA)
# ============================================================

class SupervisionDirecta(models.Model):
    """
    Tabla para manejar casos donde un supervisor de nivel superior
    supervisa directamente a un subordinado saltando niveles jerárquicos.
    
    Ejemplo: Gerente supervisa directamente a Vendedores
    """
    TIPOS_SUPERVISION = [
        ('GERENTE_TO_VENDEDOR', 'Gerente supervisa Vendedor directamente'),
        ('GERENTE_TO_TEAMLEADER', 'Gerente supervisa Team Leader directamente'),
        ('JEFE_TO_VENDEDOR', 'Jefe Venta supervisa Vendedor directamente'),
    ]
    
    # Quién supervisa (debe estar en una de las tablas de jerarquía)
    supervisor = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='subordinados_directos',
        help_text='Usuario que actúa como supervisor directo'
    )
    
    # A quién supervisa (debe estar en una tabla de jerarquía)
    subordinado = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='supervisores_directos',
        help_text='Usuario que reporta directamente al supervisor'
    )
    
    # En qué equipo se da esta supervisión
    equipo_venta = models.ForeignKey(
        EquipoVenta, 
        on_delete=models.CASCADE, 
        related_name='supervisiones_directas'
    )
    
    # Tipo de supervisión directa
    tipo_supervision = models.CharField(
        max_length=50, 
        choices=TIPOS_SUPERVISION,
        help_text='Tipo de relación de supervisión directa'
    )
    
    # Control de estado
    activo = models.BooleanField(
        default=True,
        help_text='Si esta supervisión directa está activa'
    )
    
    # Fechas de auditoría
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(
        null=True, 
        blank=True,
        help_text='Fecha cuando terminó esta supervisión directa'
    )
    
    # Notas adicionales
    notas = models.TextField(
        blank=True,
        help_text='Notas adicionales sobre esta supervisión directa'
    )
    
    class Meta:
        verbose_name = 'Supervisión Directa'
        verbose_name_plural = 'Supervisiones Directas'
        # Un subordinado solo puede tener una supervisión directa activa por equipo
        unique_together = ['subordinado', 'equipo_venta', 'activo']
        ordering = ['-fecha_inicio']
    
    def clean(self):
        """Validaciones personalizadas del modelo"""
        from django.core.exceptions import ValidationError
        
        # Validar que supervisor y subordinado son diferentes
        if self.supervisor == self.subordinado:
            raise ValidationError('Un usuario no puede supervisarse a sí mismo.')
        
        # Validar que ambos usuarios pertenecen al equipo de venta
        # (Esta validación se puede hacer más específica según tu lógica de negocio)
        
        # Si está marcado como inactivo, debe tener fecha_fin
        if not self.activo and not self.fecha_fin:
            from django.utils import timezone
            self.fecha_fin = timezone.now()
    
    def save(self, *args, **kwargs):
        """Override save para validaciones adicionales"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        estado = "Activa" if self.activo else "Inactiva"
        return f"{self.get_tipo_supervision_display()} - {self.supervisor.get_full_name()} → {self.subordinado.get_full_name()} ({estado})"
    
    def desactivar(self):
        """Método para desactivar la supervisión directa"""
        from django.utils import timezone
        self.activo = False
        self.fecha_fin = timezone.now()
        self.save()
    
    def get_supervisor_rol_en_equipo(self):
        """Obtiene el rol del supervisor en el equipo"""
        # Buscar en qué tabla de jerarquía está el supervisor para este equipo
        if self.supervisor.gerente_equipos.filter(equipo_venta=self.equipo_venta, activo=True).exists():
            return 'GERENTE'
        elif self.supervisor.jefe_ventas.filter(gerente_equipo__equipo_venta=self.equipo_venta, activo=True).exists():
            return 'JEFE_VENTA'
        elif self.supervisor.team_leaders.filter(jefe_venta__gerente_equipo__equipo_venta=self.equipo_venta, activo=True).exists():
            return 'TEAM_LEADER'
        return 'DESCONOCIDO'
    
    def get_subordinado_rol_en_equipo(self):
        """Obtiene el rol del subordinado en el equipo"""
        # Buscar en qué tabla de jerarquía está el subordinado para este equipo
        if self.subordinado.vendedores.filter(team_leader__jefe_venta__gerente_equipo__equipo_venta=self.equipo_venta, activo=True).exists():
            return 'VENDEDOR'
        elif self.subordinado.team_leaders.filter(jefe_venta__gerente_equipo__equipo_venta=self.equipo_venta, activo=True).exists():
            return 'TEAM_LEADER'
        elif self.subordinado.jefe_ventas.filter(gerente_equipo__equipo_venta=self.equipo_venta, activo=True).exists():
            return 'JEFE_VENTA'
        return 'DESCONOCIDO'


# ============================================================
# COMISIONES
# ============================================================



class ComisionVenta(models.Model):
    """Comisiones para el equipo de ventas"""
    equipo_venta = models.OneToOneField(EquipoVenta, on_delete=models.CASCADE, related_name='comision_venta')
    porcentaje_gerente_equipo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    porcentaje_jefe_venta = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    porcentaje_team_leader = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    porcentaje_vendedor = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comisión de Venta'
        verbose_name_plural = 'Comisiones de Venta'

    def __str__(self):
        return f"Comisión Venta - {self.equipo_venta.nombre}"

    def total_porcentaje(self):
        """Calcula el total de porcentajes asignados"""
        return (self.porcentaje_gerente_equipo +
                self.porcentaje_jefe_venta +
                self.porcentaje_team_leader +
                self.porcentaje_vendedor)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.total_porcentaje() > 100:
            raise ValidationError('La suma de los porcentajes no puede exceder 100%.')
