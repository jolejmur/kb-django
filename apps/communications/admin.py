# apps/whatsapp_business/admin.py
from django.contrib import admin
from .models import (
    WhatsAppConfig, Cliente, Lead, Conversacion, Mensaje, TipoPago,
    ProcesoVenta, VentaInmutable, Contrato, SeguimientoLead,
    AsignacionLead, Cita, WhatsAppTemplate, CampañaMarketing,
    LeadDistributionConfig, LeadAssignment
)


@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(admin.ModelAdmin):
    list_display = ['phone_number_id', 'business_account_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['phone_number_id', 'business_account_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['numero_whatsapp', 'nombre', 'apellido', 'email', 'origen', 'estado', 'is_active', 'created_at']
    list_filter = ['origen', 'estado', 'is_active', 'created_at']
    search_fields = ['numero_whatsapp', 'nombre', 'apellido', 'email', 'cedula']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'origen', 'prioridad', 'estado', 'is_active', 'fecha_primera_interaccion']
    list_filter = ['origen', 'prioridad', 'estado', 'is_active', 'fecha_primera_interaccion']
    search_fields = ['cliente__nombre', 'cliente__apellido', 'interes_inicial']
    readonly_fields = ['fecha_primera_interaccion', 'created_at', 'updated_at']
    raw_id_fields = ['cliente']


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
    list_display = ['codigo_proceso', 'cliente', 'inmueble', 'estado', 'etapa', 'valor_final', 'fecha_inicio']  # 'vendedor' comentado
    list_filter = ['estado', 'etapa', 'tipo_pago', 'is_active', 'fecha_inicio']
    search_fields = ['codigo_proceso', 'cliente__nombre', 'cliente__apellido', 'inmueble__codigo']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['inmueble', 'cliente', 'lead', 'tipo_pago']  # 'vendedor', 'team_leader' comentados


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
    list_display = ['lead', 'tipo_asignacion', 'fecha_asignacion', 'is_active']  # 'vendedor', 'team_leader' comentados
    list_filter = ['tipo_asignacion', 'is_active', 'fecha_asignacion']
    search_fields = ['lead__cliente__nombre', 'vendedor__usuario__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['lead', 'asignado_por', 'reasignado_por']  # 'team_leader', 'vendedor' comentados


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'tipo_cita', 'fecha_cita', 'estado', 'inmueble']  # 'vendedor' comentado
    list_filter = ['tipo_cita', 'subtipo_cita', 'estado', 'fecha_cita']
    search_fields = ['cliente__nombre', 'cliente__apellido', 'descripcion']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['lead', 'proceso_venta', 'cliente', 'inmueble', 'cita_padre']  # 'vendedor' comentado


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


@admin.register(LeadDistributionConfig)
class LeadDistributionConfigAdmin(admin.ModelAdmin):
    list_display = ['organizational_unit', 'is_active_for_leads', 'distribution_percentage', 'max_leads_per_day', 'max_leads_per_week']
    list_filter = ['is_active_for_leads', 'organizational_unit__unit_type', 'created_at']
    search_fields = ['organizational_unit__name', 'organizational_unit__code']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['organizational_unit', 'created_by', 'last_modified_by']
    
    fieldsets = (
        ('Configuración Principal', {
            'fields': ('organizational_unit', 'is_active_for_leads', 'distribution_percentage')
        }),
        ('Límites de Leads', {
            'fields': ('max_leads_per_day', 'max_leads_per_week')
        }),
        ('Notas y Comentarios', {
            'fields': ('notes',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'last_modified_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeadAssignment)
class LeadAssignmentAdmin(admin.ModelAdmin):
    list_display = ['lead', 'organizational_unit', 'assigned_to_user', 'assignment_type', 'status', 'assigned_date']
    list_filter = ['assignment_type', 'status', 'assigned_date', 'organizational_unit__unit_type', 'is_active']
    search_fields = [
        'lead__cliente__nombre', 'lead__cliente__apellido', 'lead__cliente__numero_whatsapp',
        'organizational_unit__name', 'assigned_to_user__first_name', 'assigned_to_user__last_name'
    ]
    readonly_fields = ['assigned_date', 'created_at', 'updated_at']
    raw_id_fields = ['lead', 'organizational_unit', 'assigned_to_user', 'assigned_by']
    
    fieldsets = (
        ('Asignación Principal', {
            'fields': ('lead', 'organizational_unit', 'assigned_to_user')
        }),
        ('Detalles de Asignación', {
            'fields': ('assignment_type', 'status', 'assigned_by', 'assigned_date')
        }),
        ('Estado y Notas', {
            'fields': ('is_active', 'notes')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'lead__cliente', 'organizational_unit', 'assigned_to_user', 'assigned_by'
        )