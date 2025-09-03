# apps/sales_team_management/models.py
# MODELOS NORMALIZADOS PARA SISTEMA DE JERARQUÍAS SIN DUPLICACIÓN

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class OrganizationalUnit(models.Model):
    """Unidad organizacional flexible para equipos de cualquier tipo"""
    UNIT_TYPES = [
        ('SALES', 'Equipo de Ventas'),
        ('PORTFOLIO', 'Equipo de Carteras'),
        ('MARKETING', 'Equipo de Marketing'),
        ('OPERATIONS', 'Operaciones'),
        ('SUPPORT', 'Soporte'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre de la Unidad')
    code = models.CharField(max_length=20, unique=True, verbose_name='Código', blank=True)
    description = models.TextField(blank=True, verbose_name='Descripción')
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES, verbose_name='Tipo de Unidad')
    parent_unit = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    public_registration_enabled = models.BooleanField(default=False, verbose_name='Registro Público Habilitado', 
                                                    help_text='Permite que los usuarios se auto-registren en esta unidad sin necesidad de login')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.code:
            # Generar código automáticamente basado en el tipo y nombre
            unit_prefix = self.unit_type[:3] if self.unit_type else 'ORG'
            # Tomar las primeras 3 letras del nombre, eliminar espacios y convertir a mayúsculas
            name_part = ''.join(self.name.split())[:10].upper() if self.name else 'UNIT'
            base_code = f"{unit_prefix}-{name_part}"
            
            # Asegurar unicidad
            counter = 1
            code = base_code
            while OrganizationalUnit.objects.filter(code=code).exists():
                code = f"{base_code}-{counter}"
                counter += 1
            
            self.code = code
        
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Unidad Organizacional'
        verbose_name_plural = 'Unidades Organizacionales'
        ordering = ['unit_type', 'name']
        db_table = 'sales_team_management_organizationalunit'

    def __str__(self):
        return f"{self.name} ({self.get_unit_type_display()})"


class PositionType(models.Model):
    """Tipos de posiciones configurables para unidades organizacionales"""
    code = models.CharField(max_length=30, unique=True, verbose_name='Código')
    name = models.CharField(max_length=100, verbose_name='Nombre')
    applicable_unit_types = models.CharField(max_length=200, verbose_name='Tipos de Unidad Aplicables')
    hierarchy_level = models.PositiveIntegerField(verbose_name='Nivel Jerárquico')
    can_supervise = models.BooleanField(default=False, verbose_name='Puede Supervisar')
    can_have_direct_reports = models.BooleanField(default=False, verbose_name='Puede tener Reportes Directos')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tipo de Posición'
        verbose_name_plural = 'Tipos de Posiciones'
        ordering = ['hierarchy_level', 'name']
        db_table = 'sales_team_management_positiontype'

    def __str__(self):
        return f"{self.name} (Nivel {self.hierarchy_level})"


class TeamMembership(models.Model):
    """Membresía de un usuario en una unidad organizacional con una posición específica"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Activo'),
        ('SUSPENDED', 'Suspendido'),
        ('TERMINATED', 'Terminado'),
    ]
    
    ASSIGNMENT_TYPES = [
        ('PERMANENT', 'Permanente'),
        ('TEMPORARY', 'Temporal'),
        ('PROJECT', 'Por Proyecto'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    organizational_unit = models.ForeignKey(OrganizationalUnit, on_delete=models.CASCADE)
    position_type = models.ForeignKey(PositionType, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES, default='PERMANENT')
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Membresía de Equipo'
        verbose_name_plural = 'Membresías de Equipo'
        ordering = ['-created_at']
        db_table = 'sales_team_management_teammembership'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position_type.name} en {self.organizational_unit.name}"


class HierarchyRelation(models.Model):
    """Relaciones jerárquicas entre membresías de equipo"""
    RELATION_TYPES = [
        ('NORMAL', 'Jerarquía Normal'),
        ('DIRECT', 'Supervisión Directa'),
        ('MATRIX', 'Estructura Matricial'),
        ('PROJECT', 'Por Proyecto'),
    ]
    
    AUTHORITY_LEVELS = [
        ('FULL', 'Autoridad Completa'),
        ('FUNCTIONAL', 'Autoridad Funcional'),
        ('ADMINISTRATIVE', 'Autoridad Administrativa'),
    ]
    
    supervisor_membership = models.ForeignKey(TeamMembership, on_delete=models.CASCADE, related_name='subordinate_relations')
    subordinate_membership = models.ForeignKey(TeamMembership, on_delete=models.CASCADE, related_name='supervisor_relations')
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPES, default='NORMAL')
    authority_level = models.CharField(max_length=20, choices=AUTHORITY_LEVELS, default='FULL')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    justification = models.TextField(blank=True)
    is_primary = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Relación Jerárquica'
        verbose_name_plural = 'Relaciones Jerárquicas'
        ordering = ['-created_at']
        db_table = 'sales_team_management_hierarchyrelation'

    def __str__(self):
        return f"{self.supervisor_membership.user.get_full_name()} → {self.subordinate_membership.user.get_full_name()}"


class CommissionStructure(models.Model):
    """Estructura de comisiones para unidades organizacionales"""
    COMMISSION_TYPES = [
        ('SALES', 'Comisiones de Venta'),
        ('PORTFOLIO', 'Comisiones de Cartera'),
        ('HYBRID', 'Comisiones Híbridas'),
    ]
    
    organizational_unit = models.ForeignKey(OrganizationalUnit, on_delete=models.CASCADE)
    structure_name = models.CharField(max_length=100)
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPES)
    position_percentages = models.JSONField(default=dict, help_text='Porcentajes por posición')
    effective_from = models.DateTimeField(default=timezone.now)
    effective_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Estructura de Comisiones'
        verbose_name_plural = 'Estructuras de Comisiones'
        ordering = ['-effective_from']
        db_table = 'sales_team_management_commissionstructure'

    def __str__(self):
        return f"{self.structure_name} - {self.organizational_unit.name}"


# ============================================================
# LEGACY MODELS ELIMINADOS - MIGRACION 0008 COMPLETADA
# Las tablas legacy fueron eliminadas exitosamente de la base de datos
# ============================================================