# apps/whatsapp_business/admin.py
from django.contrib import admin
from .models import (
    WhatsAppConfig, Cliente, Lead, Conversacion, Mensaje, TipoPago,
    ProcesoVenta, VentaInmutable, Contrato, SeguimientoLead,
    AsignacionLead, Cita, WhatsAppTemplate, CampañaMarketing
)


@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(admin.ModelAdmin):
    list_display = ['phone_number_id', 'business_account_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['phone_number_id', 'business_account_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['numero_whatsapp', 'nombre', 'apellido', 'email', 'origen', 'vendedor_asignado', 'is_active', 'created_at']
    list_filter = ['origen', 'is_active', 'created_at', 'vendedor_asignado']
    search_fields = ['numero_whatsapp', 'nombre', 'apellido', 'email', 'cedula']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['vendedor_asignado', 'team_leader_asignado']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'inmueble', 'origen', 'prioridad', 'is_active', 'fecha_primera_interaccion']
    list_filter = ['origen', 'prioridad', 'is_active', 'fecha_primera_interaccion']
    search_fields = ['cliente__nombre', 'cliente__apellido', 'inmueble__codigo']
    readonly_fields = ['fecha_primera_interaccion', 'created_at', 'updated_at']
    raw_id_fields = ['cliente', 'inmueble']


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'numero_whatsapp', 'estado', 'mensajes_no_leidos', 'ultimo_mensaje_at']
    list_filter = ['estado', 'is_active', 'created_at']
    search_fields = ['numero_whatsapp', 'cliente__nombre', 'cliente__apellido']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['cliente']


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ['conversacion', 'tipo', 'direccion', 'estado', 'timestamp_whatsapp', 'enviado_por']
    list_filter = ['tipo', 'direccion', 'estado', 'timestamp_whatsapp']
    search_fields = ['whatsapp_message_id', 'contenido', 'conversacion__cliente__nombre']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['conversacion', 'enviado_por', 'leido_por']


@admin.register(TipoPago)
class TipoPagoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'requiere_entidad_financiera', 'requiere_evaluacion_crediticia', 'dias_financiamiento', 'is_active']
    list_filter = ['requiere_entidad_financiera', 'requiere_evaluacion_crediticia', 'is_active']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProcesoVenta)
class ProcesoVentaAdmin(admin.ModelAdmin):
    list_display = ['codigo_proceso', 'cliente', 'inmueble', 'vendedor', 'estado', 'etapa', 'valor_final', 'fecha_inicio']
    list_filter = ['estado', 'etapa', 'tipo_pago', 'is_active', 'fecha_inicio']
    search_fields = ['codigo_proceso', 'cliente__nombre', 'cliente__apellido', 'inmueble__codigo']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['inmueble', 'cliente', 'lead', 'vendedor', 'team_leader', 'tipo_pago']


@admin.register(VentaInmutable)
class VentaInmutableAdmin(admin.ModelAdmin):
    list_display = ['codigo_venta', 'fecha_venta', 'valor_final', 'tipo_pago', 'proceso_venta']
    list_filter = ['fecha_venta', 'tipo_pago']
    search_fields = ['codigo_venta', 'proceso_venta__codigo_proceso']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['proceso_venta']


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['numero_contrato', 'fecha_firma', 'venta_inmutable']
    list_filter = ['fecha_firma']
    search_fields = ['numero_contrato', 'venta_inmutable__codigo_venta']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['venta_inmutable']


@admin.register(SeguimientoLead)
class SeguimientoLeadAdmin(admin.ModelAdmin):
    list_display = ['lead', 'tipo_actividad', 'resultado', 'fecha_actividad', 'usuario']
    list_filter = ['tipo_actividad', 'resultado', 'fecha_actividad']
    search_fields = ['lead__cliente__nombre', 'descripcion']
    readonly_fields = ['created_at']
    raw_id_fields = ['lead', 'proceso_venta', 'usuario']


@admin.register(AsignacionLead)
class AsignacionLeadAdmin(admin.ModelAdmin):
    list_display = ['lead', 'vendedor', 'team_leader', 'tipo_asignacion', 'fecha_asignacion', 'is_active']
    list_filter = ['tipo_asignacion', 'is_active', 'fecha_asignacion']
    search_fields = ['lead__cliente__nombre', 'vendedor__usuario__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['lead', 'team_leader', 'vendedor', 'asignado_por', 'reasignado_por']


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'tipo_cita', 'fecha_cita', 'estado', 'vendedor', 'inmueble']
    list_filter = ['tipo_cita', 'subtipo_cita', 'estado', 'fecha_cita']
    search_fields = ['cliente__nombre', 'cliente__apellido', 'descripcion']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['lead', 'proceso_venta', 'vendedor', 'cliente', 'inmueble', 'cita_padre']


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'language', 'status', 'is_active', 'created_by']
    list_filter = ['category', 'language', 'status', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['created_by']


@admin.register(CampañaMarketing)
class CampañaMarketingAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'estado', 'fecha_inicio', 'fecha_fin', 'created_by']
    list_filter = ['tipo', 'estado', 'fecha_inicio', 'is_active']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['template', 'created_by']