from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
import os

User = get_user_model()


class EventoComercial(models.Model):
    """
    Modelo para gestionar eventos comerciales donde los vendedores pueden invitar clientes
    """
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Evento")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    fecha_inicio = models.DateTimeField(verbose_name="Fecha y Hora de Inicio")
    fecha_fin = models.DateTimeField(verbose_name="Fecha y Hora de Fin")
    ubicacion = models.CharField(max_length=300, verbose_name="Ubicación")
    activo = models.BooleanField(default=True, verbose_name="Evento Activo")
    
    # Configuración del evento
    permite_invitaciones = models.BooleanField(default=True, verbose_name="Permitir Invitaciones")
    requiere_registro_cliente = models.BooleanField(default=True, verbose_name="Requiere Registro de Cliente")
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                   related_name='eventos_creados', verbose_name="Creado por")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    class Meta:
        verbose_name = "Evento Comercial"
        verbose_name_plural = "Eventos Comerciales"
        ordering = ['-fecha_inicio']
        permissions = [
            ('view_evento_reports', 'Can view event reports'),
            ('manage_eventos', 'Can manage all events'),
        ]
    
    def __str__(self):
        return f"{self.nombre} - {self.fecha_inicio.strftime('%d/%m/%Y')}"
    
    @property
    def esta_activo(self):
        """Verifica si el evento está activo y dentro del período válido"""
        now = timezone.now()
        return self.activo and self.fecha_inicio <= now <= self.fecha_fin
    
    @property
    def total_invitaciones(self):
        """Total de invitaciones generadas para este evento"""
        return self.invitaciones.count()
    
    @property
    def total_visitas(self):
        """Total de visitas registradas para este evento"""
        return VisitaEvento.objects.filter(invitacion__evento=self).count()


class InvitacionQR(models.Model):
    """
    Modelo para gestionar las invitaciones QR que generan los vendedores
    """
    # Identificador único para el QR
    codigo_qr = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name="Código QR")
    
    # Relaciones
    evento = models.ForeignKey(EventoComercial, on_delete=models.CASCADE, 
                              related_name='invitaciones', verbose_name="Evento")
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, 
                                related_name='invitaciones_generadas', verbose_name="Vendedor")
    
    # Información de la invitación
    activa = models.BooleanField(default=True, verbose_name="Invitación Activa")
    usos_maximos = models.PositiveIntegerField(default=1, verbose_name="Usos Máximos")
    usos_actuales = models.PositiveIntegerField(default=0, verbose_name="Usos Actuales")
    vistas_qr = models.PositiveIntegerField(default=0, verbose_name="Vistas del QR")
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_expiracion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Expiración")
    
    # Archivo QR (opcional, para descarga)
    archivo_qr = models.ImageField(upload_to='qr_codes/', null=True, blank=True, verbose_name="Archivo QR")
    
    class Meta:
        verbose_name = "Invitación QR"
        verbose_name_plural = "Invitaciones QR"
        ordering = ['-fecha_creacion']
        unique_together = ['evento', 'vendedor']  # Un QR por vendedor por evento
    
    def __str__(self):
        return f"QR {self.vendedor.get_full_name()} - {self.evento.nombre}"
    
    def get_equipo_vendedor(self):
        """Obtiene el equipo de venta del vendedor"""
        equipo = self.vendedor.get_equipo_venta()
        return equipo.nombre if equipo else "Sin equipo asignado"
    
    def save(self, *args, **kwargs):
        """Generar archivo QR automáticamente al guardar"""
        super().save(*args, **kwargs)
        if not self.archivo_qr:
            self.generar_qr()
    
    def generar_qr(self):
        """Genera el código QR como imagen con información completa"""
        # Información completa para el QR
        vendedor_nombre = self.vendedor.get_full_name() or self.vendedor.username
        equipo_nombre = self.get_equipo_vendedor()
        
        # QR Code con URL segura usando subdominio - Bypass completo del middleware Django
        qr_data = f"https://qrkorban.duckdns.org/{self.codigo_qr}/"
        
        # Crear QR optimizado para URLs (más compacto y legible)
        qr = qrcode.QRCode(
            version=1,  # Versión pequeña para URLs cortas
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,  # Tamaño mayor para mejor escaneo
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Crear imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Guardar en archivo temporal
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_{self.vendedor.id}_{self.evento.id}_{self.codigo_qr}.png'
        
        self.archivo_qr.save(filename, File(buffer), save=False)
        buffer.close()
        
        # Guardar el modelo
        super().save(update_fields=['archivo_qr'])
    
    @property
    def puede_usar(self):
        """Verifica si la invitación puede ser usada"""
        if not self.activa:
            return False
        if self.usos_actuales >= self.usos_maximos:
            return False
        if self.fecha_expiracion and timezone.now() > self.fecha_expiracion:
            return False
        return True
    
    @property
    def total_visitas(self):
        """Total de visitas usando esta invitación"""
        return self.visitas.count()


class VisitaEvento(models.Model):
    """
    Modelo para registrar las visitas de clientes a eventos usando QR
    """
    # Relación con la invitación QR
    invitacion = models.ForeignKey(InvitacionQR, on_delete=models.CASCADE, 
                                  related_name='visitas', verbose_name="Invitación QR")
    
    # Datos del cliente (requeridos)
    nombre_cliente = models.CharField(max_length=200, verbose_name="Nombre del Cliente")
    cedula_cliente = models.CharField(max_length=20, verbose_name="Cédula del Cliente")
    telefono_cliente = models.CharField(max_length=20, verbose_name="Teléfono del Cliente")
    
    # Datos adicionales del cliente (opcionales)
    email_cliente = models.EmailField(blank=True, verbose_name="Email del Cliente")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Información del registro
    fecha_visita = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Visita")
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                      related_name='visitas_registradas', 
                                      verbose_name="Registrado por")
    
    # Estado del cliente
    ESTADO_CHOICES = [
        ('registrado', 'Registrado'),
        ('atendido', 'Atendido'),
        ('interesado', 'Interesado'),
        ('no_interesado', 'No Interesado'),
        ('seguimiento', 'En Seguimiento'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, 
                             default='registrado', verbose_name="Estado")
    
    class Meta:
        verbose_name = "Visita a Evento"
        verbose_name_plural = "Visitas a Eventos"
        ordering = ['-fecha_visita']
        unique_together = ['invitacion', 'cedula_cliente']  # Evitar duplicados por cédula en mismo evento
    
    def __str__(self):
        return f"{self.nombre_cliente} - {self.invitacion.evento.nombre}"
    
    @property
    def vendedor(self):
        """Vendedor que generó la invitación"""
        return self.invitacion.vendedor
    
    @property
    def evento(self):
        """Evento asociado a través de la invitación"""
        return self.invitacion.evento
    
    def save(self, *args, **kwargs):
        """Actualizar contador de usos en la invitación"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Incrementar el contador de usos de la invitación
            self.invitacion.usos_actuales += 1
            self.invitacion.save(update_fields=['usos_actuales'])


# Modelo para estadísticas rápidas (opcional)
class EstadisticaEvento(models.Model):
    """
    Modelo para almacenar estadísticas pre-calculadas de eventos
    """
    evento = models.OneToOneField(EventoComercial, on_delete=models.CASCADE, 
                                 related_name='estadisticas', verbose_name="Evento")
    
    total_invitaciones = models.PositiveIntegerField(default=0)
    total_visitas = models.PositiveIntegerField(default=0)
    total_clientes_unicos = models.PositiveIntegerField(default=0)
    
    # Por vendedor (JSON field para estadísticas detalladas)
    estadisticas_vendedores = models.JSONField(default=dict, blank=True)
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Estadística de Evento"
        verbose_name_plural = "Estadísticas de Eventos"
    
    def actualizar_estadisticas(self):
        """Actualiza las estadísticas del evento"""
        evento = self.evento
        
        self.total_invitaciones = evento.invitaciones.count()
        self.total_visitas = VisitaEvento.objects.filter(invitacion__evento=evento).count()
        self.total_clientes_unicos = VisitaEvento.objects.filter(
            invitacion__evento=evento
        ).values('cedula_cliente').distinct().count()
        
        # Estadísticas por vendedor
        vendedores_stats = {}
        for invitacion in evento.invitaciones.all():
            vendedor_id = str(invitacion.vendedor.id)
            vendedor_name = invitacion.vendedor.get_full_name() or invitacion.vendedor.username
            
            vendedores_stats[vendedor_id] = {
                'nombre': vendedor_name,
                'invitaciones': 1,
                'visitas': invitacion.visitas.count(),
                'clientes_unicos': invitacion.visitas.values('cedula_cliente').distinct().count()
            }
        
        self.estadisticas_vendedores = vendedores_stats
        self.save()