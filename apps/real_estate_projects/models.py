# apps/real_estate_projects/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


# ============================================================
# ROLES ESPECÍFICOS DE DESARROLLO DE PROYECTOS
# ============================================================

class GerenteProyecto(models.Model):
    """Gerente de Proyecto - Nivel más alto en desarrollo"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gerente_proyectos')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Gerente de Proyecto'
        verbose_name_plural = 'Gerentes de Proyecto'

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - Gerente de Proyecto"


class JefeProyecto(models.Model):
    """Jefe de Proyecto - Reporta al Gerente de Proyecto"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jefe_proyectos')
    gerente_proyecto = models.ForeignKey(GerenteProyecto, on_delete=models.CASCADE, related_name='jefeproyectos')
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Jefe de Proyecto'
        verbose_name_plural = 'Jefes de Proyecto'

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - Jefe de Proyecto"


# ============================================================
# PROYECTOS INMOBILIARIOS
# ============================================================

class Proyecto(models.Model):
    """
    Modelo para representar proyectos inmobiliarios.
    Los proyectos pueden ser de tipo terrenos o departamentos.
    Se dividen en fases para organizar la entrega.
    """
    ESTADOS_PROYECTO = [
        ('planificacion', 'Planificación'),
        ('desarrollo', 'En Desarrollo'),
        ('construccion', 'En Construcción'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]

    TIPOS_PROYECTO = [
        ('terrenos', 'Terrenos'),
        ('departamentos', 'Departamentos'),
    ]

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS_PROYECTO, default='departamentos')
    estado = models.CharField(max_length=20, choices=ESTADOS_PROYECTO, default='planificacion')
    
    # Precio base del proyecto
    precio_base_m2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('1000.00'),
        help_text="Precio base por metro cuadrado del proyecto (se hereda a las fases)"
    )

    # Responsables del proyecto
    gerente_proyecto = models.ForeignKey(
        GerenteProyecto,
        on_delete=models.PROTECT,
        related_name='proyectos'
    )
    jefe_proyecto = models.ForeignKey(
        JefeProyecto,
        on_delete=models.PROTECT,
        related_name='proyectos',
        null=True,
        blank=True
    )

    # Equipos de venta asignados (relación con la otra app)
    organizational_units = models.ManyToManyField(
        'sales_team_management.OrganizationalUnit',
        through='AsignacionEquipoProyecto',
        related_name='proyectos'
    )

    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-created_at']

    def __str__(self):
        return self.nombre

    @property
    def total_inmuebles(self):
        """Cuenta el total de inmuebles del proyecto"""
        total = 0
        for fase in self.fases.all():
            total += fase.total_inmuebles
        return total

    @property
    def inmuebles_disponibles(self):
        """Cuenta los inmuebles disponibles"""
        total = 0
        for fase in self.fases.all():
            total += fase.inmuebles_disponibles
        return total

    @property
    def inmuebles_vendidos(self):
        """Cuenta los inmuebles vendidos"""
        total = 0
        for fase in self.fases.all():
            total += fase.inmuebles_vendidos
        return total

    @property
    def porcentaje_vendido(self):
        """Calcula el porcentaje de inmuebles vendidos"""
        total = self.total_inmuebles
        if total == 0:
            return 0
        return round((self.inmuebles_vendidos / total) * 100, 2)


    def can_be_deleted(self):
        """Verifica si el proyecto puede ser eliminado"""
        # No se puede eliminar si tiene fases con inmuebles
        for fase in self.fases.all():
            if fase.total_inmuebles > 0:
                return False
        return True


class AsignacionEquipoProyecto(models.Model):
    """
    Tabla intermedia para la relación muchos a muchos entre Proyecto y EquipoVenta.
    Permite tener información adicional sobre la asignación.
    """
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    organizational_unit = models.ForeignKey('sales_team_management.OrganizationalUnit', on_delete=models.CASCADE)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Asignación Equipo-Proyecto'
        verbose_name_plural = 'Asignaciones Equipo-Proyecto'
        unique_together = ['proyecto', 'organizational_unit']

    def __str__(self):
        return f"{self.organizational_unit.name} - {self.proyecto.nombre}"


# ============================================================
# ESTRUCTURA DE FASES
# ============================================================

class Fase(models.Model):
    """
    Modelo para representar fases de un proyecto.
    Las fases dividen el proyecto en etapas de entrega.
    """
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='fases')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    numero_fase = models.PositiveIntegerField()
    fecha_inicio_prevista = models.DateField(null=True, blank=True)
    fecha_entrega_prevista = models.DateField(null=True, blank=True)
    fecha_entrega_real = models.DateField(null=True, blank=True)
    
    # Control de precios y comercialización
    precio_m2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('1000.00'),
        help_text="Precio por metro cuadrado para inmuebles de esta fase"
    )
    
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fase'
        verbose_name_plural = 'Fases'
        ordering = ['proyecto', 'numero_fase']
        unique_together = ['proyecto', 'numero_fase']

    def __str__(self):
        return f"{self.proyecto.nombre} - Fase {self.numero_fase}: {self.nombre}"

    @property
    def total_inmuebles(self):
        """Cuenta el total de inmuebles de la fase"""
        if self.proyecto.tipo == 'departamentos':
            total = 0
            for torre in self.torres.all():
                total += torre.total_inmuebles
            return total
        else:  # terrenos
            total = 0
            for sector in self.sectores.all():
                total += sector.total_inmuebles
            return total

    @property
    def inmuebles_disponibles(self):
        """Cuenta los inmuebles disponibles de la fase"""
        return self.inmuebles.filter(disponible=True, estado='disponible').count()

    @property
    def inmuebles_vendidos(self):
        """Cuenta los inmuebles vendidos de la fase"""
        return self.inmuebles.filter(estado='vendido').count()
    
    @property
    def es_comercializable(self):
        """Verifica si la fase tiene inmuebles comercializables"""
        return self.inmuebles.filter(disponible_comercializacion=True).exists()
    
    @property
    def inmuebles_comercializables(self):
        """Cuenta los inmuebles comercializables de la fase"""
        return self.inmuebles.filter(disponible_comercializacion=True).count()
    
    def marcar_comercializable(self, estado=True):
        """Marca todos los inmuebles de la fase como comercializables o no"""
        return self.inmuebles.update(disponible_comercializacion=estado)


# ============================================================
# MODELOS PARA PROYECTOS DE DEPARTAMENTOS
# ============================================================

class Torre(models.Model):
    """
    Modelo para representar torres en proyectos de departamentos.
    """
    fase = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='torres')
    nombre = models.CharField(max_length=50)
    numero_torre = models.PositiveIntegerField()
    numero_pisos = models.PositiveIntegerField()
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Torre'
        verbose_name_plural = 'Torres'
        ordering = ['fase', 'numero_torre']
        unique_together = ['fase', 'numero_torre']

    def __str__(self):
        return f"{self.fase.proyecto.nombre} - Fase {self.fase.numero_fase} - Torre {self.numero_torre}"

    @property
    def total_inmuebles(self):
        """Cuenta el total de inmuebles de la torre"""
        total = 0
        for piso in self.pisos.all():
            total += piso.total_inmuebles
        return total
    
    @property
    def es_comercializable(self):
        """Verifica si la torre tiene inmuebles comercializables"""
        return Inmueble.objects.filter(
            piso__torre=self,
            disponible_comercializacion=True
        ).exists()
    
    @property
    def inmuebles_comercializables(self):
        """Cuenta los inmuebles comercializables de la torre"""
        return Inmueble.objects.filter(
            piso__torre=self,
            disponible_comercializacion=True
        ).count()
    
    def marcar_comercializable(self, estado=True):
        """Marca todos los inmuebles de la torre como comercializables o no"""
        return Inmueble.objects.filter(
            piso__torre=self
        ).update(disponible_comercializacion=estado)


class Piso(models.Model):
    """
    Modelo para representar pisos dentro de una torre.
    """
    torre = models.ForeignKey(Torre, on_delete=models.CASCADE, related_name='pisos')
    numero_piso = models.PositiveIntegerField()
    nombre = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Piso'
        verbose_name_plural = 'Pisos'
        ordering = ['torre', 'numero_piso']
        unique_together = ['torre', 'numero_piso']

    def __str__(self):
        return f"Torre {self.torre.numero_torre} - Piso {self.numero_piso}"

    @property
    def total_inmuebles(self):
        """Cuenta el total de inmuebles del piso"""
        return self.inmuebles.count()


# ============================================================
# MODELOS PARA PROYECTOS DE TERRENOS
# ============================================================

class Sector(models.Model):
    """
    Modelo para representar sectores en proyectos de terrenos.
    """
    fase = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='sectores')
    nombre = models.CharField(max_length=50)
    numero_sector = models.PositiveIntegerField()
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sector'
        verbose_name_plural = 'Sectores'
        ordering = ['fase', 'numero_sector']
        unique_together = ['fase', 'numero_sector']

    def __str__(self):
        return f"{self.fase.proyecto.nombre} - Fase {self.fase.numero_fase} - Sector {self.numero_sector}"

    @property
    def total_inmuebles(self):
        """Cuenta el total de inmuebles del sector"""
        total = 0
        for manzana in self.manzanas.all():
            total += manzana.total_inmuebles
        return total
    
    @property
    def es_comercializable(self):
        """Verifica si el sector tiene inmuebles comercializables"""
        return Inmueble.objects.filter(
            manzana__sector=self,
            disponible_comercializacion=True
        ).exists()
    
    @property
    def inmuebles_comercializables(self):
        """Cuenta los inmuebles comercializables del sector"""
        return Inmueble.objects.filter(
            manzana__sector=self,
            disponible_comercializacion=True
        ).count()
    
    def marcar_comercializable(self, estado=True):
        """Marca todos los inmuebles del sector como comercializables o no"""
        return Inmueble.objects.filter(
            manzana__sector=self
        ).update(disponible_comercializacion=estado)


class Manzana(models.Model):
    """
    Modelo para representar manzanas dentro de un sector.
    """
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='manzanas')
    numero_manzana = models.PositiveIntegerField()
    nombre = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Manzana'
        verbose_name_plural = 'Manzanas'
        ordering = ['sector', 'numero_manzana']
        unique_together = ['sector', 'numero_manzana']

    def __str__(self):
        return f"Sector {self.sector.numero_sector} - Manzana {self.numero_manzana}"

    @property
    def total_inmuebles(self):
        """Cuenta el total de inmuebles de la manzana"""
        return self.inmuebles.count()


# ============================================================
# PONDERADORES DE PRECIO
# ============================================================

class Ponderador(models.Model):
    """
    Modelo para ponderadores flexibles de precio con sistema jerárquico e historial.
    Permite crear factores de ajuste en diferentes niveles: proyecto, fase, inmueble.
    """
    NIVELES_APLICACION = [
        ('proyecto', 'Todo el Proyecto'),
        ('fase', 'Solo la Fase'),
        ('inmueble', 'Inmuebles Específicos'),
    ]
    
    TIPOS_PONDERADOR = [
        ('valorizacion', 'Valorización'),
        ('descuento', 'Descuento'),
        ('promocion', 'Promoción Temporal'),
        ('ubicacion', 'Por Ubicación'),
        ('infraestructura', 'Infraestructura'),
        ('comercial', 'Estrategia Comercial'),
    ]
    
    # Relaciones jerárquicas
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name='ponderadores',
        help_text="Proyecto al que pertenece este ponderador"
    )
    fase = models.ForeignKey(
        'Fase',
        on_delete=models.CASCADE,
        related_name='ponderadores',
        null=True,
        blank=True,
        help_text="Fase específica (solo si nivel_aplicacion es 'fase')"
    )
    
    # Configuración del ponderador
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo del ponderador (ej: 'Nuevo puente', 'Descuento lanzamiento')"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_PONDERADOR,
        default='valorizacion',
        help_text="Tipo de ponderador para mejor organización"
    )
    nivel_aplicacion = models.CharField(
        max_length=20,
        choices=NIVELES_APLICACION,
        default='proyecto',
        help_text="Nivel donde se aplica este ponderador"
    )
    
    # Valores (pueden ser porcentaje O monto fijo)
    porcentaje = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('-100.00')), MaxValueValidator(Decimal('500.00'))],
        null=True,
        blank=True,
        help_text="Porcentaje de ajuste (ej: 15.00 = +15%, -5.00 = -5%)"
    )
    monto_fijo = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monto fijo a agregar/quitar (alternativo al porcentaje)"
    )
    
    # Control temporal y historial
    fecha_activacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora desde cuando está activo el ponderador"
    )
    fecha_desactivacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora hasta cuando está activo (opcional para permanentes)"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Estado actual del ponderador"
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Versión del ponderador para historial"
    )
    ponderador_padre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versiones_hijo',
        help_text="Ponderador anterior del cual deriva esta versión"
    )
    
    # Metadatos y control de usuario
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción detallada del ponderador"
    )
    justificacion = models.TextField(
        blank=True,
        help_text="Razón o justificación para este ponderador/cambio"
    )
    
    # Control de auditoría
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ponderadores_creados',
        null=True,
        blank=True,
        help_text="Usuario que creó este ponderador"
    )
    activated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ponderadores_activados',
        null=True,
        blank=True,
        help_text="Usuario que activó este ponderador"
    )
    deactivated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ponderadores_desactivados',
        null=True,
        blank=True,
        help_text="Usuario que desactivó este ponderador"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ponderador de Precio'
        verbose_name_plural = 'Ponderadores de Precio'
        ordering = ['proyecto', 'nivel_aplicacion', 'tipo', 'nombre']
        indexes = [
            models.Index(fields=['proyecto', 'activo']),
            models.Index(fields=['fase', 'activo']),
            models.Index(fields=['fecha_activacion', 'fecha_desactivacion']),
        ]

    def __str__(self):
        if self.monto_fijo:
            valor = f"${self.monto_fijo:,.0f}"
        else:
            signo = "+" if self.porcentaje >= 0 else ""
            valor = f"{signo}{self.porcentaje}%"
        
        nivel = dict(self.NIVELES_APLICACION)[self.nivel_aplicacion]
        return f"{self.nombre} ({valor}) - {nivel}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que tenga porcentaje O monto fijo, no ambos
        if self.porcentaje is not None and self.monto_fijo is not None:
            raise ValidationError("No puede tener tanto porcentaje como monto fijo. Elija uno.")
        
        if self.porcentaje is None and self.monto_fijo is None:
            raise ValidationError("Debe especificar un porcentaje O un monto fijo.")
        
        # Validar que si nivel es 'fase', debe tener fase asignada
        if self.nivel_aplicacion == 'fase' and not self.fase:
            raise ValidationError("Si el nivel de aplicación es 'fase', debe seleccionar una fase.")
        
        # Validar que la fase pertenezca al proyecto
        if self.fase and self.fase.proyecto != self.proyecto:
            raise ValidationError("La fase seleccionada no pertenece al proyecto.")
        
        # Validar fechas
        if self.fecha_desactivacion and self.fecha_activacion >= self.fecha_desactivacion:
            raise ValidationError("La fecha de desactivación debe ser posterior a la fecha de activación.")

    @property
    def factor_multiplicador(self):
        """Devuelve el factor multiplicador para aplicar al precio"""
        if self.porcentaje is not None:
            return Decimal('1') + (self.porcentaje / Decimal('100'))
        return Decimal('1')  # Para montos fijos no se usa multiplicador

    @property
    def valor_display(self):
        """Devuelve el valor formateado para mostrar"""
        if self.monto_fijo:
            return f"${self.monto_fijo:,.0f}"
        else:
            signo = "+" if self.porcentaje >= 0 else ""
            return f"{signo}{self.porcentaje}%"

    @property
    def esta_vigente(self):
        """Verifica si el ponderador está vigente en este momento"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.activo:
            return False
        
        if self.fecha_activacion > now:
            return False
        
        if self.fecha_desactivacion and self.fecha_desactivacion <= now:
            return False
        
        return True

    def activar(self, usuario):
        """Activa el ponderador"""
        from django.utils import timezone
        self.activo = True
        self.activated_by = usuario
        if not self.fecha_activacion:
            self.fecha_activacion = timezone.now()
        self.save()

    def desactivar(self, usuario, fecha_desactivacion=None):
        """Desactiva el ponderador"""
        from django.utils import timezone
        self.activo = False
        self.deactivated_by = usuario
        self.fecha_desactivacion = fecha_desactivacion or timezone.now()
        self.save()

    def crear_nueva_version(self, usuario, **nuevos_datos):
        """Crea una nueva versión de este ponderador"""
        # Desactivar la versión actual
        self.desactivar(usuario)
        
        # Crear nueva versión
        nueva_version = Ponderador.objects.create(
            proyecto=self.proyecto,
            fase=self.fase,
            nombre=nuevos_datos.get('nombre', self.nombre),
            tipo=nuevos_datos.get('tipo', self.tipo),
            nivel_aplicacion=nuevos_datos.get('nivel_aplicacion', self.nivel_aplicacion),
            porcentaje=nuevos_datos.get('porcentaje', self.porcentaje),
            monto_fijo=nuevos_datos.get('monto_fijo', self.monto_fijo),
            fecha_activacion=nuevos_datos.get('fecha_activacion'),
            fecha_desactivacion=nuevos_datos.get('fecha_desactivacion'),
            descripcion=nuevos_datos.get('descripcion', self.descripcion),
            justificacion=nuevos_datos.get('justificacion', ''),
            created_by=usuario,
            activated_by=usuario,
            activo=True,
            version=self.version + 1,
            ponderador_padre=self
        )
        
        return nueva_version


# ============================================================
# INMUEBLES
# ============================================================

class Inmueble(models.Model):
    """
    Modelo para representar inmuebles dentro de un proyecto.
    Los inmuebles pueden ser departamentos o terrenos según el tipo de proyecto.
    """
    TIPOS_INMUEBLE = [
        # Para departamentos
        ('departamento', 'Departamento'),
        ('penthouse', 'Penthouse'),
        ('local', 'Local Comercial'),
        ('oficina', 'Oficina'),
        ('bodega', 'Bodega'),
        ('parqueadero', 'Parqueadero'),
        # Para terrenos
        ('terreno', 'Terreno'),
        ('lote', 'Lote'),
    ]

    ESTADOS_INMUEBLE = [
        ('disponible', 'Disponible'),
        ('reservado', 'Reservado'),
        ('vendido', 'Vendido'),
        ('bloqueado', 'Bloqueado'),
    ]


    # Relaciones principales
    fase = models.ForeignKey(Fase, on_delete=models.CASCADE, related_name='inmuebles')
    
    # Relaciones específicas según tipo de proyecto
    # Para departamentos
    piso = models.ForeignKey(Piso, on_delete=models.CASCADE, related_name='inmuebles', null=True, blank=True)
    
    # Para terrenos
    manzana = models.ForeignKey(Manzana, on_delete=models.CASCADE, related_name='inmuebles', null=True, blank=True)

    # Campos básicos
    codigo = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPOS_INMUEBLE)
    m2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Área en metros cuadrados"
    )
    
    # Campos para ajustes de precio (opcionales)
    factor_precio = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('1.0000'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Factor multiplicador sobre el precio base de la fase (1.0 = sin ajuste)"
    )
    precio_manual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio manual que sobrescribe el cálculo automático"
    )
    
    # Ponderadores de precio
    ponderadores = models.ManyToManyField(
        'Ponderador',
        blank=True,
        related_name='inmuebles',
        help_text="Ponderadores que afectan el precio de este inmueble"
    )
    
    estado = models.CharField(max_length=20, choices=ESTADOS_INMUEBLE, default='disponible')
    caracteristicas = models.TextField(blank=True)
    disponible = models.BooleanField(default=True)
    disponible_comercializacion = models.BooleanField(
        default=False,
        help_text="Indica si el inmueble está disponible para comercialización"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inmueble'
        verbose_name_plural = 'Inmuebles'
        ordering = ['fase', 'codigo']
        unique_together = ['fase', 'codigo']

    def __str__(self):
        return f"{self.fase.proyecto.nombre} - {self.codigo}"

    @property
    def precio_calculado(self):
        """Calcula el precio automáticamente con sistema jerárquico de ponderadores"""
        if self.precio_manual:
            return self.precio_manual
        
        if self.m2 > 0 and self.fase.precio_m2:
            from django.utils import timezone
            from django.db.models import Q
            from itertools import chain
            
            precio_base = self.m2 * self.fase.precio_m2 * self.factor_precio
            monto_adicional = Decimal('0')
            factor_total = Decimal('1')
            now = timezone.now()
            
            # 1. Ponderadores de PROYECTO (afectan todo el proyecto)
            ponderadores_proyecto = self.fase.proyecto.ponderadores.filter(
                activo=True,
                nivel_aplicacion='proyecto',
                fecha_activacion__lte=now
            ).filter(
                Q(fecha_desactivacion__isnull=True) | Q(fecha_desactivacion__gte=now)
            )
            
            # 2. Ponderadores de FASE (afectan solo esta fase)
            ponderadores_fase = self.fase.ponderadores.filter(
                activo=True,
                nivel_aplicacion='fase',
                fecha_activacion__lte=now
            ).filter(
                Q(fecha_desactivacion__isnull=True) | Q(fecha_desactivacion__gte=now)
            )
            
            # 3. Ponderadores de INMUEBLE (específicos de este inmueble)
            ponderadores_inmueble = self.ponderadores.filter(
                activo=True,
                nivel_aplicacion='inmueble',
                fecha_activacion__lte=now
            ).filter(
                Q(fecha_desactivacion__isnull=True) | Q(fecha_desactivacion__gte=now)
            )
            
            # Aplicar todos los ponderadores vigentes
            for ponderador in chain(ponderadores_proyecto, ponderadores_fase, ponderadores_inmueble):
                if ponderador.monto_fijo:
                    # Montos fijos se suman directamente al precio base
                    monto_adicional += ponderador.monto_fijo
                else:
                    # Porcentajes se multiplican como factores
                    factor_total *= ponderador.factor_multiplicador
            
            # Calcular precio final: (precio_base + montos_fijos) * factores_porcentuales
            precio_final = (precio_base + monto_adicional) * factor_total
            return round(precio_final, 2)
        
        return Decimal('0')

    @property
    def precio_por_m2(self):
        """Devuelve el precio por metro cuadrado del inmueble"""
        if self.m2 > 0:
            return round(self.precio_calculado / self.m2, 2)
        return Decimal('0')

    @property
    def precio_venta(self):
        """Precio de venta del inmueble (calculado automáticamente)"""
        return self.precio_calculado
    
    @property
    def resumen_ponderadores(self):
        """Devuelve un resumen de los ponderadores aplicados"""
        ponderadores_activos = self.ponderadores.filter(activo=True)
        if not ponderadores_activos.exists():
            return "Sin ponderadores aplicados"
        
        detalles = []
        porcentaje_total = Decimal('0')
        
        for ponderador in ponderadores_activos:
            detalles.append(f"{ponderador.nombre}: {'+' if ponderador.porcentaje >= 0 else ''}{ponderador.porcentaje}%")
            porcentaje_total += ponderador.porcentaje
        
        resumen = ", ".join(detalles)
        total_str = f" (Total: {'+' if porcentaje_total >= 0 else ''}{porcentaje_total}%)"
        
        return resumen + total_str

    @property
    def ubicacion_completa(self):
        """Devuelve la ubicación completa del inmueble"""
        if self.piso:  # Departamento
            return f"Torre {self.piso.torre.numero_torre} - Piso {self.piso.numero_piso}"
        elif self.manzana:  # Terreno
            return f"Sector {self.manzana.sector.numero_sector} - Manzana {self.manzana.numero_manzana}"
        return "Sin ubicación específica"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que tenga la ubicación correcta según el tipo de proyecto
        if self.fase.proyecto.tipo == 'departamentos':
            if not self.piso:
                raise ValidationError('Los inmuebles de proyectos de departamentos deben tener un piso asignado.')
            if self.manzana:
                raise ValidationError('Los inmuebles de departamentos no pueden tener manzana asignada.')
        elif self.fase.proyecto.tipo == 'terrenos':
            if not self.manzana:
                raise ValidationError('Los inmuebles de proyectos de terrenos deben tener una manzana asignada.')
            if self.piso:
                raise ValidationError('Los inmuebles de terrenos no pueden tener piso asignado.')


# ============================================================
# COMISIONES DE DESARROLLO
# ============================================================

class ComisionDesarrollo(models.Model):
    """Comisiones para el equipo de desarrollo del proyecto"""
    proyecto = models.OneToOneField(Proyecto, on_delete=models.CASCADE, related_name='comision_desarrollo')
    porcentaje_gerente_proyecto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    porcentaje_jefe_proyecto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comisión de Desarrollo'
        verbose_name_plural = 'Comisiones de Desarrollo'

    def __str__(self):
        return f"Comisión Desarrollo - {self.proyecto.nombre}"

    def total_porcentaje(self):
        """Calcula el total de porcentajes asignados"""
        return self.porcentaje_gerente_proyecto + self.porcentaje_jefe_proyecto

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.total_porcentaje() > 100:
            raise ValidationError('La suma de los porcentajes no puede exceder 100%.')