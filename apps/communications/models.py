# apps/whatsapp_business/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError

User = get_user_model()


# ============================================================
# CONFIGURACIÓN WHATSAPP BUSINESS
# ============================================================

class WhatsAppConfig(models.Model):
    """
    Configuración para WhatsApp Business API
    """
    phone_number_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="ID del número de teléfono de WhatsApp Business"
    )
    business_account_id = models.CharField(
        max_length=100,
        help_text="ID de la cuenta comercial de WhatsApp"
    )
    whatsapp_business_account_id = models.CharField(
        max_length=100,
        help_text="ID de la cuenta de WhatsApp Business",
        blank=True,
        null=True
    )
    access_token = models.CharField(
        max_length=500,
        help_text="Token de acceso para la API de WhatsApp"
    )
    app_secret = models.CharField(
        max_length=100,
        help_text="Secreto de la aplicación de Facebook",
        blank=True
    )
    webhook_verify_token = models.CharField(
        max_length=100,
        help_text="Token de verificación del webhook"
    )
    webhook_url = models.URLField(
        help_text="URL del webhook para recibir mensajes"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la configuración está activa"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración WhatsApp'
        verbose_name_plural = 'Configuraciones WhatsApp'

    def __str__(self):
        return f"WhatsApp Config - {self.phone_number_id}"
    
    def save(self, *args, **kwargs):
        # Generar app_secret automáticamente si no existe
        if not self.app_secret:
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            self.app_secret = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        super().save(*args, **kwargs)


# ============================================================
# CLIENTES Y CONTACTOS
# ============================================================

class Cliente(models.Model):
    """
    Modelo para clientes/contactos de WhatsApp
    """
    ORIGENES_CLIENTE = [
        ('whatsapp', 'WhatsApp'),
        ('referido', 'Referido'),
        ('publicidad', 'Publicidad'),
        ('feria', 'Feria'),
        ('telefono', 'Teléfono'),
        ('web', 'Página Web'),
        ('otro', 'Otro')
    ]
    
    ESTADOS_CLIENTE = [
        ('prospecto', 'Prospecto'),
        ('cliente_activo', 'Cliente Activo'),
        ('cliente_inactivo', 'Cliente Inactivo'),
        ('perdido', 'Perdido')
    ]

    numero_whatsapp = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número de WhatsApp del cliente en formato internacional"
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre del cliente"
    )
    apellido = models.CharField(
        max_length=100,
        blank=True,
        help_text="Apellido del cliente"
    )
    email = models.EmailField(
        blank=True,
        help_text="Email del cliente"
    )
    cedula = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="Cédula o documento de identidad"
    )
    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha de nacimiento"
    )
    domicilio = models.CharField(
        max_length=255,
        blank=True,
        help_text="Dirección del domicilio"
    )
    latitud = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        blank=True,
        null=True,
        help_text="Latitud de la ubicación"
    )
    longitud = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        blank=True,
        null=True,
        help_text="Longitud de la ubicación"
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGENES_CLIENTE,
        default='whatsapp',
        help_text="Origen del cliente"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_CLIENTE,
        default='prospecto',
        help_text="Estado del cliente: prospecto inicial, cliente activo (compró), etc."
    )
    etiquetas = models.TextField(
        blank=True,
        help_text="Etiquetas o categorías del cliente (JSON)"
    )
    
    # Asignación de vendedores - TEMPORALMENTE DESHABILITADO PARA REFACTOR
    # vendedor_asignado = models.ForeignKey(
    #     'sales_team_management.Vendedor',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='clientes_asignados',
    #     help_text="Vendedor asignado al cliente"
    # )
    # team_leader_asignado = models.ForeignKey(
    #     'sales_team_management.TeamLeader',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='clientes_asignados',
    #     help_text="Team Leader asignado al cliente"
    # )
    fecha_primera_asignacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de la primera asignación"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el cliente está activo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.numero_whatsapp})"

    @property
    def nombre_completo(self):
        """Devuelve el nombre completo del cliente"""
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def tiene_coordenadas(self):
        """Verifica si el cliente tiene coordenadas geográficas"""
        return self.latitud is not None and self.longitud is not None

    def get_coordenadas(self):
        """Obtiene las coordenadas como tupla"""
        if self.tiene_coordenadas:
            return (float(self.latitud), float(self.longitud))
        return None


# ============================================================
# LEADS SIMPLIFICADOS
# ============================================================

class Lead(models.Model):
    """
    Modelo simplificado para leads - Solo prospección inicial
    """
    PRIORIDADES = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
    ]

    ORIGENES_LEAD = [
        ('whatsapp', 'WhatsApp'),
        ('referido', 'Referido'),
        ('publicidad', 'Publicidad'),
        ('feria', 'Feria'),
        ('telefono', 'Teléfono'),
        ('web', 'Página Web'),
        ('otro', 'Otro')
    ]

    ESTADOS_LEAD = [
        ('nuevo', 'Nuevo'),
        ('asignado', 'Asignado'),
        ('en_proceso', 'En Proceso'),
        ('calificado', 'Calificado'),
        ('rechazado', 'Rechazado'),
        ('convertido', 'Convertido')
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='leads',
        help_text="Cliente que genera el lead"
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGENES_LEAD,
        default='whatsapp',
        help_text="Origen del lead"
    )
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDADES,
        default='media',
        help_text="Prioridad del lead"
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADOS_LEAD,
        default='nuevo',
        help_text="Estado actual del lead"
    )
    interes_inicial = models.TextField(
        blank=True,
        help_text="Descripción del interés inicial"
    )
    notas = models.TextField(
        blank=True,
        help_text="Notas adicionales sobre el lead"
    )
    fecha_primera_interaccion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de la primera interacción"
    )
    fecha_ultima_interaccion = models.DateTimeField(
        auto_now=True,
        help_text="Fecha de la última interacción"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el lead está activo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-fecha_ultima_interaccion']

    def __str__(self):
        return f"Lead: {self.cliente.nombre_completo} - {self.estado}"


# ============================================================
# CONVERSACIONES Y MENSAJES
# ============================================================

class Conversacion(models.Model):
    """
    Modelo para conversaciones de WhatsApp
    """
    ESTADOS_CONVERSACION = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
        ('archivada', 'Archivada')
    ]

    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name='conversacion',
        help_text="Cliente de la conversación"
    )
    numero_whatsapp = models.CharField(
        max_length=20,
        help_text="Número de WhatsApp de la conversación"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_CONVERSACION,
        default='abierta',
        help_text="Estado de la conversación"
    )
    ultimo_mensaje_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha del último mensaje"
    )
    mensajes_no_leidos = models.IntegerField(
        default=0,
        help_text="Número de mensajes no leídos"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la conversación está activa"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'
        ordering = ['-ultimo_mensaje_at']

    def __str__(self):
        return f"Conversación: {self.cliente.nombre_completo}"


class Mensaje(models.Model):
    """
    Modelo para mensajes de WhatsApp
    """
    TIPOS_MENSAJE = [
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Documento'),
        ('location', 'Ubicación'),
        ('template', 'Plantilla'),
        ('interactive', 'Interactivo'),
        ('contacts', 'Contacto')
    ]

    DIRECCIONES_MENSAJE = [
        ('incoming', 'Entrante'),
        ('outgoing', 'Saliente')
    ]

    ESTADOS_MENSAJE = [
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('leido', 'Leído'),
        ('error', 'Error')
    ]

    conversacion = models.ForeignKey(
        Conversacion,
        on_delete=models.CASCADE,
        related_name='mensajes',
        help_text="Conversación a la que pertenece el mensaje"
    )
    whatsapp_message_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="ID del mensaje en WhatsApp"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_MENSAJE,
        default='text',
        help_text="Tipo de mensaje"
    )
    direccion = models.CharField(
        max_length=20,
        choices=DIRECCIONES_MENSAJE,
        help_text="Dirección del mensaje"
    )
    contenido = models.TextField(
        blank=True,
        help_text="Contenido del mensaje"
    )
    media_url = models.URLField(
        blank=True,
        help_text="URL del archivo multimedia"
    )
    media_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Tipo de archivo multimedia"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_MENSAJE,
        default='enviado',
        help_text="Estado del mensaje"
    )
    timestamp_whatsapp = models.DateTimeField(
        help_text="Timestamp del mensaje de WhatsApp"
    )
    
    # Usuario que envió el mensaje (si es saliente)
    enviado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensajes_enviados',
        help_text="Usuario que envió el mensaje"
    )
    
    # Usuario que leyó el mensaje
    leido_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensajes_leidos',
        help_text="Usuario que leyó el mensaje"
    )
    fecha_lectura = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de lectura del mensaje"
    )
    
    # Campos para archivos multimedia
    archivo_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL temporal de WhatsApp para descargar el archivo"
    )
    archivo_local = models.FileField(
        upload_to='whatsapp_media/%Y/%m/',
        null=True,
        blank=True,
        help_text="Archivo descargado y almacenado localmente"
    )
    archivo_tipo_mime = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Tipo MIME del archivo (image/jpeg, audio/ogg, etc.)"
    )
    archivo_nombre = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Nombre original del archivo"
    )
    archivo_tamaño = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Tamaño del archivo en bytes"
    )
    caption = models.TextField(
        null=True,
        blank=True,
        help_text="Caption/descripción para imágenes y videos"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
        ordering = ['-timestamp_whatsapp']

    def __str__(self):
        return f"Mensaje {self.tipo} - {self.conversacion.cliente.nombre_completo}"


# ============================================================
# TIPOS DE PAGO
# ============================================================

class TipoPago(models.Model):
    """
    Modelo para tipos de pago disponibles
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre del tipo de pago (ej: efectivo, crédito directo)"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción del tipo de pago"
    )
    requiere_entidad_financiera = models.BooleanField(
        default=False,
        help_text="Indica si requiere entidad financiera"
    )
    requiere_evaluacion_crediticia = models.BooleanField(
        default=False,
        help_text="Indica si requiere evaluación crediticia"
    )
    dias_financiamiento = models.IntegerField(
        default=0,
        help_text="Días de financiamiento disponibles"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el tipo de pago está activo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tipo de Pago'
        verbose_name_plural = 'Tipos de Pago'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# ============================================================
# PROCESO DE VENTA
# ============================================================

class ProcesoVenta(models.Model):
    """
    Proceso de venta conectado directamente al inmueble
    """
    ESTADOS_PROCESO = [
        ('prospecto', 'Prospecto'),
        ('calificado', 'Calificado'),
        ('propuesta', 'Propuesta'),
        ('negociacion', 'Negociación'),
        ('cerrado_ganado', 'Cerrado - Ganado'),
        ('cerrado_perdido', 'Cerrado - Perdido'),
        ('pausado', 'Pausado')
    ]

    ETAPAS_PROCESO = [
        ('contacto_inicial', 'Contacto Inicial'),
        ('presentacion_producto', 'Presentación del Producto'),
        ('visita_inmueble', 'Visita al Inmueble'),
        ('propuesta_comercial', 'Propuesta Comercial'),
        ('negociacion_precio', 'Negociación de Precio'),
        ('evaluacion_credito', 'Evaluación de Crédito'),
        ('firma_contrato', 'Firma de Contrato'),
        ('entrega_inmueble', 'Entrega del Inmueble')
    ]

    # Relaciones principales
    inmueble = models.ForeignKey(
        'real_estate_projects.Inmueble',
        on_delete=models.CASCADE,
        related_name='procesos_venta',
        help_text="Inmueble que se está vendiendo"
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='procesos_venta',
        help_text="Cliente comprador"
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='procesos_venta',
        help_text="Lead que originó el proceso (opcional)"
    )
    
    # Equipo de ventas - TEMPORALMENTE DESHABILITADO PARA REFACTOR
    # vendedor = models.ForeignKey(
    #     'sales_team_management.Vendedor',
    #     on_delete=models.PROTECT,
    #     related_name='procesos_venta',
    #     help_text="Vendedor responsable"
    # )
    # team_leader = models.ForeignKey(
    #     'sales_team_management.TeamLeader',
    #     on_delete=models.PROTECT,
    #     related_name='procesos_venta',
    #     help_text="Team Leader supervisor"
    # )
    
    # Información del proceso
    codigo_proceso = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único del proceso de venta"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_PROCESO,
        default='prospecto',
        help_text="Estado actual del proceso"
    )
    etapa = models.CharField(
        max_length=30,
        choices=ETAPAS_PROCESO,
        default='contacto_inicial',
        help_text="Etapa actual del proceso"
    )
    
    # Fechas importantes
    fecha_inicio = models.DateField(
        auto_now_add=True,
        help_text="Fecha de inicio del proceso"
    )
    fecha_cierre = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de cierre del proceso"
    )
    
    # Información comercial
    valor_inmueble = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Valor original del inmueble"
    )
    valor_negociado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Valor final negociado"
    )
    descuento = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Descuento aplicado"
    )
    
    # Información de pago
    tipo_pago = models.ForeignKey(
        TipoPago,
        on_delete=models.PROTECT,
        related_name='procesos_venta',
        help_text="Tipo de pago seleccionado"
    )
    entidad_financiera = models.CharField(
        max_length=200,
        blank=True,
        help_text="Entidad financiera (si aplica)"
    )
    evaluacion_crediticia = models.CharField(
        max_length=50,
        blank=True,
        help_text="Resultado de la evaluación crediticia"
    )
    
    # Fechas del proceso
    fecha_evaluacion_credito = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de evaluación crediticia"
    )
    fecha_promesa_pago = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de promesa de pago"
    )
    fecha_firma_contrato = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de firma del contrato"
    )
    fecha_entrega_inmueble = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de entrega del inmueble"
    )
    
    # Información adicional
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones del proceso"
    )
    motivo_perdida = models.TextField(
        blank=True,
        help_text="Motivo de pérdida (si aplica)"
    )
    probabilidad_cierre = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Probabilidad de cierre (%)"
    )
    
    # Próxima acción
    proxima_accion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Próxima acción planificada"
    )
    fecha_proxima_accion = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de la próxima acción"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el proceso está activo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proceso de Venta'
        verbose_name_plural = 'Procesos de Venta'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.codigo_proceso} - {self.cliente.nombre_completo}"

    def clean(self):
        """Validaciones del modelo"""
        if self.valor_negociado and self.valor_negociado > self.valor_inmueble + self.descuento:
            raise ValidationError("El valor negociado no puede ser mayor al valor del inmueble más el descuento")
        
        if self.fecha_cierre and self.fecha_cierre < self.fecha_inicio:
            raise ValidationError("La fecha de cierre no puede ser anterior a la fecha de inicio")

    def save(self, *args, **kwargs):
        """Generar código de proceso si no existe"""
        if not self.codigo_proceso:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.codigo_proceso = f"PV-{timestamp}"
        
        # Establecer valor inicial del inmueble
        if not self.valor_inmueble:
            self.valor_inmueble = self.inmueble.precio_calculado
        
        super().save(*args, **kwargs)

    @property
    def valor_final(self):
        """Calcula el valor final considerando descuentos"""
        if self.valor_negociado:
            return self.valor_negociado
        return self.valor_inmueble - self.descuento

    @property
    def porcentaje_descuento(self):
        """Calcula el porcentaje de descuento aplicado"""
        if self.valor_inmueble > 0:
            return (self.descuento / self.valor_inmueble) * 100
        return 0

    @property
    def dias_en_proceso(self):
        """Calcula los días en proceso"""
        from django.utils import timezone
        if self.fecha_cierre:
            return (self.fecha_cierre - self.fecha_inicio).days
        return (timezone.now().date() - self.fecha_inicio).days


# ============================================================
# VENTA INMUTABLE (SNAPSHOT)
# ============================================================

class VentaInmutable(models.Model):
    """
    Snapshot inmutable de la venta al momento del cierre
    """
    proceso_venta = models.OneToOneField(
        ProcesoVenta,
        on_delete=models.CASCADE,
        related_name='venta_inmutable',
        help_text="Proceso de venta que generó esta venta"
    )
    codigo_venta = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único de la venta"
    )
    fecha_venta = models.DateField(
        help_text="Fecha de la venta"
    )
    valor_final = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Valor final de la venta"
    )
    descuento_aplicado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Descuento aplicado"
    )
    tipo_pago = models.CharField(
        max_length=100,
        help_text="Tipo de pago utilizado"
    )
    entidad_financiera = models.CharField(
        max_length=200,
        blank=True,
        help_text="Entidad financiera utilizada"
    )
    
    # Snapshots inmutables (JSON)
    cliente_snapshot = models.JSONField(
        help_text="Snapshot del cliente al momento de la venta"
    )
    inmueble_snapshot = models.JSONField(
        help_text="Snapshot del inmueble al momento de la venta"
    )
    vendedor_snapshot = models.JSONField(
        help_text="Snapshot del vendedor al momento de la venta"
    )
    team_leader_snapshot = models.JSONField(
        help_text="Snapshot del team leader al momento de la venta"
    )
    equipo_venta_snapshot = models.JSONField(
        help_text="Snapshot del equipo de venta al momento de la venta"
    )
    comisiones_snapshot = models.JSONField(
        help_text="Snapshot de las comisiones al momento de la venta"
    )
    ponderadores_aplicados = models.JSONField(
        help_text="Snapshot de los ponderadores aplicados"
    )
    
    # Información adicional
    precio_m2_momento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio por m2 al momento de la venta"
    )
    m2_inmueble = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Metros cuadrados del inmueble"
    )
    ubicacion_inmueble = models.CharField(
        max_length=200,
        help_text="Ubicación del inmueble"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Venta Inmutable'
        verbose_name_plural = 'Ventas Inmutables'
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"{self.codigo_venta} - {self.fecha_venta}"

    def save(self, *args, **kwargs):
        """Generar código de venta si no existe"""
        if not self.codigo_venta:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.codigo_venta = f"VT-{timestamp}"
        
        super().save(*args, **kwargs)


# ============================================================
# CONTRATO
# ============================================================

class Contrato(models.Model):
    """
    Contrato asociado a la venta inmutable (relación 1:1)
    """
    venta_inmutable = models.OneToOneField(
        VentaInmutable,
        on_delete=models.CASCADE,
        related_name='contrato',
        help_text="Venta inmutable asociada"
    )
    numero_contrato = models.CharField(
        max_length=100,
        unique=True,
        help_text="Número único del contrato"
    )
    fecha_firma = models.DateField(
        help_text="Fecha de firma del contrato"
    )
    archivo_contrato = models.FileField(
        upload_to='contratos/',
        blank=True,
        help_text="Archivo PDF del contrato"
    )
    clausulas_especiales = models.TextField(
        blank=True,
        help_text="Cláusulas especiales del contrato"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones del contrato"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        ordering = ['-fecha_firma']

    def __str__(self):
        return f"Contrato {self.numero_contrato} - {self.fecha_firma}"

    def save(self, *args, **kwargs):
        """Generar número de contrato si no existe"""
        if not self.numero_contrato:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.numero_contrato = f"CT-{timestamp}"
        
        super().save(*args, **kwargs)


# ============================================================
# SEGUIMIENTO DE LEADS
# ============================================================

class SeguimientoLead(models.Model):
    """
    Historial de seguimiento de leads
    """
    TIPOS_ACTIVIDAD = [
        ('llamada', 'Llamada'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('reunion', 'Reunión'),
        ('visita', 'Visita'),
        ('propuesta', 'Propuesta'),
        ('seguimiento', 'Seguimiento'),
        ('otro', 'Otro')
    ]

    RESULTADOS = [
        ('exitoso', 'Exitoso'),
        ('pendiente', 'Pendiente'),
        ('no_respuesta', 'No Respuesta'),
        ('no_interesado', 'No Interesado'),
        ('reprogramar', 'Reprogramar')
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='seguimientos',
        help_text="Lead al que pertenece el seguimiento"
    )
    proceso_venta = models.ForeignKey(
        ProcesoVenta,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='seguimientos',
        help_text="Proceso de venta asociado"
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='seguimientos_realizados',
        help_text="Usuario que realizó el seguimiento"
    )
    tipo_actividad = models.CharField(
        max_length=20,
        choices=TIPOS_ACTIVIDAD,
        help_text="Tipo de actividad realizada"
    )
    descripcion = models.TextField(
        help_text="Descripción de la actividad"
    )
    fecha_actividad = models.DateTimeField(
        help_text="Fecha y hora de la actividad"
    )
    resultado = models.CharField(
        max_length=20,
        choices=RESULTADOS,
        help_text="Resultado de la actividad"
    )
    proxima_accion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Próxima acción planificada"
    )
    fecha_proxima_accion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de la próxima acción"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seguimiento de Lead'
        verbose_name_plural = 'Seguimientos de Leads'
        ordering = ['-fecha_actividad']

    def __str__(self):
        return f"Seguimiento {self.tipo_actividad} - {self.lead}"


# ============================================================
# ASIGNACIONES DE LEADS
# ============================================================

class AsignacionLead(models.Model):
    """
    Historial de asignaciones de leads
    """
    TIPOS_ASIGNACION = [
        ('automatica', 'Automática'),
        ('manual', 'Manual'),
        ('reasignacion', 'Reasignación')
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='asignaciones',
        help_text="Lead asignado"
    )
    # TEMPORALMENTE DESHABILITADO PARA REFACTOR
    # team_leader = models.ForeignKey(
    #     'sales_team_management.TeamLeader',
    #     on_delete=models.CASCADE,
    #     related_name='asignaciones_leads',
    #     help_text="Team Leader asignado"
    # )
    # vendedor = models.ForeignKey(
    #     'sales_team_management.Vendedor',
    #     on_delete=models.CASCADE,
    #     related_name='asignaciones_leads',
    #     help_text="Vendedor asignado"
    # )
    tipo_asignacion = models.CharField(
        max_length=20,
        choices=TIPOS_ASIGNACION,
        default='automatica',
        help_text="Tipo de asignación"
    )
    asignado_por = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='asignaciones_realizadas',
        help_text="Usuario que realizó la asignación"
    )
    fecha_asignacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de asignación"
    )
    fecha_reasignacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de reasignación"
    )
    reasignado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reasignaciones_realizadas',
        help_text="Usuario que realizó la reasignación"
    )
    motivo_reasignacion = models.TextField(
        blank=True,
        help_text="Motivo de la reasignación"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la asignación está activa"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignación de Lead'
        verbose_name_plural = 'Asignaciones de Leads'
        ordering = ['-fecha_asignacion']

    def __str__(self):
        return f"Asignación: {self.lead} -> {self.vendedor}"


# ============================================================
# CITAS Y REUNIONES
# ============================================================

class Cita(models.Model):
    """
    Citas y reuniones con clientes
    """
    TIPOS_CITA = [
        ('reunion', 'Reunión'),
        ('visita_inmueble', 'Visita al Inmueble'),
        ('presentacion', 'Presentación'),
        ('firma', 'Firma de Contrato'),
        ('entrega', 'Entrega de Inmueble'),
        ('seguimiento', 'Seguimiento'),
        ('otro', 'Otro')
    ]

    SUBTIPOS_CITA = [
        ('presencial', 'Presencial'),
        ('virtual', 'Virtual'),
        ('telefonica', 'Telefónica'),
        ('whatsapp', 'WhatsApp')
    ]

    ESTADOS_CITA = [
        ('programada', 'Programada'),
        ('confirmada', 'Confirmada'),
        ('realizada', 'Realizada'),
        ('cancelada', 'Cancelada'),
        ('reprogramada', 'Reprogramada')
    ]

    RESULTADOS = [
        ('exitoso', 'Exitoso'),
        ('parcial', 'Parcial'),
        ('no_exitoso', 'No Exitoso'),
        ('no_asistio', 'No Asistió')
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='citas',
        help_text="Lead asociado a la cita"
    )
    proceso_venta = models.ForeignKey(
        ProcesoVenta,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='citas',
        help_text="Proceso de venta asociado"
    )
    # TEMPORALMENTE DESHABILITADO PARA REFACTOR
    # vendedor = models.ForeignKey(
    #     'sales_team_management.Vendedor',
    #     on_delete=models.CASCADE,
    #     related_name='citas',
    #     help_text="Vendedor responsable de la cita"
    # )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='citas',
        help_text="Cliente de la cita"
    )
    inmueble = models.ForeignKey(
        'real_estate_projects.Inmueble',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='citas',
        help_text="Inmueble a mostrar"
    )
    
    # Información de la cita
    tipo_cita = models.CharField(
        max_length=20,
        choices=TIPOS_CITA,
        help_text="Tipo de cita"
    )
    subtipo_cita = models.CharField(
        max_length=20,
        choices=SUBTIPOS_CITA,
        default='presencial',
        help_text="Subtipo de cita"
    )
    fecha_cita = models.DateTimeField(
        help_text="Fecha y hora de la cita"
    )
    duracion_estimada = models.IntegerField(
        default=60,
        help_text="Duración estimada en minutos"
    )
    ubicacion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Ubicación de la cita"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción de la cita"
    )
    
    # Estado y resultado
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_CITA,
        default='programada',
        help_text="Estado de la cita"
    )
    resultado = models.CharField(
        max_length=20,
        choices=RESULTADOS,
        blank=True,
        help_text="Resultado de la cita"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones de la cita"
    )
    
    # Recordatorios
    recordatorio_enviado = models.BooleanField(
        default=False,
        help_text="Indica si se envió recordatorio"
    )
    fecha_recordatorio = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha del recordatorio"
    )
    
    # Relaciones jerárquicas
    cita_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='citas_seguimiento',
        help_text="Cita padre (para seguimientos)"
    )
    numero_encuentro = models.IntegerField(
        default=1,
        help_text="Número de encuentro con el cliente"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha_cita']

    def __str__(self):
        return f"Cita {self.tipo_cita} - {self.cliente.nombre_completo} - {self.fecha_cita}"


# ============================================================
# TEMPLATES DE WHATSAPP
# ============================================================

class WhatsAppTemplate(models.Model):
    """
    Templates de WhatsApp para mensajes
    """
    CATEGORIAS = [
        ('marketing', 'Marketing'),
        ('utility', 'Utility'),
        ('authentication', 'Authentication')
    ]

    IDIOMAS = [
        ('es', 'Español'),
        ('en', 'Inglés'),
        ('pt', 'Portugués')
    ]

    ESTADOS = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('disabled', 'Deshabilitado')
    ]

    name = models.CharField(
        max_length=100,
        help_text="Nombre del template"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        help_text="Categoría del template"
    )
    language = models.CharField(
        max_length=10,
        choices=IDIOMAS,
        default='es',
        help_text="Idioma del template"
    )
    status = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='pending',
        help_text="Estado del template"
    )
    components = models.JSONField(
        help_text="Componentes del template (JSON)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='templates_creados',
        help_text="Usuario que creó el template"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el template está activo"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Template de WhatsApp'
        verbose_name_plural = 'Templates de WhatsApp'
        unique_together = ['name', 'language']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.language})"


# ============================================================
# CAMPAÑAS DE MARKETING
# ============================================================

class CampañaMarketing(models.Model):
    """
    Campañas de marketing (para futuro)
    """
    TIPOS_CAMPAÑA = [
        ('promocional', 'Promocional'),
        ('informativa', 'Informativa'),
        ('seguimiento', 'Seguimiento'),
        ('remarketing', 'Remarketing')
    ]

    ESTADOS_CAMPAÑA = [
        ('borrador', 'Borrador'),
        ('programada', 'Programada'),
        ('activa', 'Activa'),
        ('pausada', 'Pausada'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada')
    ]

    nombre = models.CharField(
        max_length=200,
        help_text="Nombre de la campaña"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción de la campaña"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_CAMPAÑA,
        help_text="Tipo de campaña"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_CAMPAÑA,
        default='borrador',
        help_text="Estado de la campaña"
    )
    template = models.ForeignKey(
        WhatsAppTemplate,
        on_delete=models.CASCADE,
        related_name='campañas',
        help_text="Template a utilizar"
    )
    audiencia_objetivo = models.JSONField(
        help_text="Criterios de audiencia objetivo (JSON)"
    )
    fecha_inicio = models.DateField(
        help_text="Fecha de inicio de la campaña"
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de fin de la campaña"
    )
    presupuesto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Presupuesto de la campaña"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='campañas_creadas',
        help_text="Usuario que creó la campaña"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la campaña está activa"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Campaña de Marketing'
        verbose_name_plural = 'Campañas de Marketing'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.nombre} ({self.estado})"


# ============================================================
# CONFIGURACIÓN DE DISTRIBUCIÓN DE LEADS
# ============================================================

class LeadDistributionConfig(models.Model):
    """
    Configuración para distribución automática de leads por fuerza de venta
    """
    organizational_unit = models.OneToOneField(
        'sales_team_management.OrganizationalUnit',
        on_delete=models.CASCADE,
        related_name='lead_distribution',
        help_text="Unidad organizacional/fuerza de venta"
    )
    is_active_for_leads = models.BooleanField(
        default=False,
        help_text="¿Esta fuerza de venta puede recibir leads automáticamente?"
    )
    distribution_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Porcentaje de leads que debe recibir esta fuerza de venta"
    )
    max_leads_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Límite máximo de leads por día (opcional)"
    )
    max_leads_per_week = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Límite máximo de leads por semana (opcional)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notas adicionales sobre la configuración"
    )
    
    # Metadatos de la configuración
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lead_distributions_created',
        help_text="Usuario que creó la configuración"
    )
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lead_distributions_modified',
        help_text="Último usuario que modificó la configuración"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración de Distribución de Leads'
        verbose_name_plural = 'Configuraciones de Distribución de Leads'
        ordering = ['organizational_unit__name']

    def __str__(self):
        return f"{self.organizational_unit.name} - {self.distribution_percentage}%"
    
    def clean(self):
        """Validaciones del modelo"""
        from django.core.exceptions import ValidationError
        
        # Verificar que el porcentaje no exceda 100%
        if self.distribution_percentage > 100:
            raise ValidationError("El porcentaje no puede ser mayor a 100%")
            
        # Verificar que la suma total de porcentajes no exceda 100%
        if self.pk:
            # Estamos editando
            other_configs = LeadDistributionConfig.objects.filter(
                is_active_for_leads=True
            ).exclude(pk=self.pk)
        else:
            # Estamos creando
            other_configs = LeadDistributionConfig.objects.filter(
                is_active_for_leads=True
            )
        
        if self.is_active_for_leads:
            total_percentage = sum(config.distribution_percentage for config in other_configs)
            total_percentage += self.distribution_percentage
            
            if total_percentage > 100:
                raise ValidationError(
                    f"La suma de todos los porcentajes activos ({total_percentage}%) "
                    f"excede el 100%. Ajuste los porcentajes."
                )

    @property
    def current_leads_today(self):
        """Cantidad de leads asignados hoy a esta fuerza de venta"""
        from django.utils import timezone
        today = timezone.now().date()
        
        return LeadAssignment.objects.filter(
            organizational_unit=self.organizational_unit,
            assigned_date__date=today,
            is_active=True
        ).count()
    
    @property
    def current_leads_this_week(self):
        """Cantidad de leads asignados esta semana a esta fuerza de venta"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        return LeadAssignment.objects.filter(
            organizational_unit=self.organizational_unit,
            assigned_date__date__gte=week_start,
            is_active=True
        ).count()
    
    @property
    def can_receive_more_leads(self):
        """Verifica si puede recibir más leads según los límites configurados"""
        if not self.is_active_for_leads:
            return False
            
        # Verificar límite diario
        if self.max_leads_per_day and self.current_leads_today >= self.max_leads_per_day:
            return False
            
        # Verificar límite semanal
        if self.max_leads_per_week and self.current_leads_this_week >= self.max_leads_per_week:
            return False
            
        return True

    @classmethod
    def get_total_active_percentage(cls):
        """Retorna el porcentaje total configurado para fuerzas de venta activas"""
        return cls.objects.filter(
            is_active_for_leads=True
        ).aggregate(
            total=models.Sum('distribution_percentage')
        )['total'] or Decimal('0.00')


class LeadAssignment(models.Model):
    """
    Historial de asignaciones de leads a fuerzas de venta
    """
    ASSIGNMENT_TYPES = [
        ('AUTOMATIC', 'Automática'),
        ('MANUAL', 'Manual'),
        ('REASSIGNMENT', 'Reasignación'),
        ('EMERGENCY', 'Emergencia'),
    ]
    
    ASSIGNMENT_STATUS = [
        ('PENDING', 'Pendiente'),
        ('ASSIGNED', 'Asignado'),
        ('ACCEPTED', 'Aceptado'),
        ('REJECTED', 'Rechazado'),
        ('TRANSFERRED', 'Transferido'),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="Lead asignado"
    )
    organizational_unit = models.ForeignKey(
        'sales_team_management.OrganizationalUnit',
        on_delete=models.CASCADE,
        related_name='lead_assignments',
        help_text="Fuerza de venta asignada"
    )
    assigned_to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        help_text="Usuario específico asignado (opcional)"
    )
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPES,
        default='AUTOMATIC',
        help_text="Tipo de asignación"
    )
    status = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_STATUS,
        default='ASSIGNED',
        help_text="Estado de la asignación"
    )
    assigned_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de asignación"
    )
    accepted_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de aceptación"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lead_assignments_made',
        null=True,
        blank=True,
        help_text="Usuario que realizó la asignación (null para asignaciones automáticas)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notas de la asignación"
    )
    distribution_config_snapshot = models.JSONField(
        help_text="Snapshot de la configuración al momento de la asignación"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="¿Es la asignación activa actual?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignación de Lead'
        verbose_name_plural = 'Asignaciones de Leads'
        ordering = ['-assigned_date']
        indexes = [
            models.Index(fields=['lead', 'is_active']),
            models.Index(fields=['organizational_unit', 'assigned_date']),
            models.Index(fields=['assigned_to_user', 'status']),
        ]

    def __str__(self):
        return f"Lead {self.lead.id} → {self.organizational_unit.name}"

    def save(self, *args, **kwargs):
        # Al crear una nueva asignación activa, desactivar las anteriores
        if self.is_active and not self.pk:
            LeadAssignment.objects.filter(
                lead=self.lead,
                is_active=True
            ).update(is_active=False)
        
        # Guardar snapshot de la configuración
        if not self.distribution_config_snapshot:
            try:
                config = LeadDistributionConfig.objects.get(
                    organizational_unit=self.organizational_unit
                )
                self.distribution_config_snapshot = {
                    'distribution_percentage': float(config.distribution_percentage),
                    'max_leads_per_day': config.max_leads_per_day,
                    'max_leads_per_week': config.max_leads_per_week,
                    'assigned_at': self.assigned_date.isoformat() if self.assigned_date else None
                }
            except LeadDistributionConfig.DoesNotExist:
                self.distribution_config_snapshot = {'error': 'Configuration not found'}
        
        super().save(*args, **kwargs)


# ============================================================
# MENSAJES DE DEBUG Y TESTING
# ============================================================

class WebhookDebugMessage(models.Model):
    """
    Modelo para almacenar mensajes de debug del webhook
    """
    TIPOS_MENSAJE = [
        ('incoming', 'Entrante'),
        ('outgoing', 'Saliente'),
        ('webhook_event', 'Evento Webhook'),
        ('test_message', 'Mensaje de Prueba')
    ]

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_MENSAJE,
        help_text="Tipo de mensaje"
    )
    numero_telefono = models.CharField(
        max_length=20,
        help_text="Número de teléfono involucrado"
    )
    contenido = models.TextField(
        help_text="Contenido del mensaje"
    )
    raw_data = models.JSONField(
        help_text="Datos raw del webhook o API"
    )
    respuesta_api = models.JSONField(
        null=True,
        blank=True,
        help_text="Respuesta de la API de WhatsApp"
    )
    estado = models.CharField(
        max_length=20,
        default='received',
        help_text="Estado del mensaje"
    )
    config_utilizada = models.ForeignKey(
        WhatsAppConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Configuración utilizada"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje de Debug'
        verbose_name_plural = 'Mensajes de Debug'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tipo} - {self.numero_telefono} - {self.created_at}"


class TestMessage(models.Model):
    """
    Modelo para almacenar configuraciones de mensajes de prueba
    """
    numero_destino = models.CharField(
        max_length=20,
        help_text="Número de destino para pruebas"
    )
    template_name = models.CharField(
        max_length=100,
        default='hello_world',
        help_text="Nombre del template a usar"
    )
    language_code = models.CharField(
        max_length=10,
        default='en_US',
        help_text="Código de idioma"
    )
    mensaje_personalizado = models.TextField(
        blank=True,
        help_text="Mensaje personalizado (opcional)"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Usuario que creó la prueba"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje de Prueba'
        verbose_name_plural = 'Mensajes de Prueba'
        ordering = ['-created_at']

    def __str__(self):
        return f"Test a {self.numero_destino} - {self.created_at}"