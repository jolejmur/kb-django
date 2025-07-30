from django.contrib import admin
from .models import EventoComercial, InvitacionQR, VisitaEvento, EstadisticaEvento


@admin.register(EventoComercial)
class EventoComercialAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'fecha_inicio', 'fecha_fin', 'ubicacion', 'activo', 'total_invitaciones', 'total_visitas']
    list_filter = ['activo', 'fecha_inicio', 'creado_por']
    search_fields = ['nombre', 'descripcion', 'ubicacion']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion', 'total_invitaciones', 'total_visitas']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'ubicacion')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Configuración', {
            'fields': ('activo', 'permite_invitaciones', 'requiere_registro_cliente')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
        ('Estadísticas', {
            'fields': ('total_invitaciones', 'total_visitas'),
            'classes': ('collapse',)
        })
    )


@admin.register(InvitacionQR)
class InvitacionQRAdmin(admin.ModelAdmin):
    list_display = ['vendedor', 'evento', 'activa', 'usos_actuales', 'usos_maximos', 'fecha_creacion', 'total_visitas']
    list_filter = ['activa', 'evento', 'fecha_creacion']
    search_fields = ['vendedor__first_name', 'vendedor__last_name', 'vendedor__username', 'evento__nombre']
    readonly_fields = ['codigo_qr', 'fecha_creacion', 'archivo_qr', 'total_visitas']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('evento', 'vendedor', 'activa')
        }),
        ('Configuración de Uso', {
            'fields': ('usos_maximos', 'usos_actuales', 'fecha_expiracion')
        }),
        ('QR Code', {
            'fields': ('codigo_qr', 'archivo_qr'),
            'classes': ('collapse',)
        }),
        ('Estadísticas', {
            'fields': ('total_visitas', 'fecha_creacion'),
            'classes': ('collapse',)
        })
    )


@admin.register(VisitaEvento)
class VisitaEventoAdmin(admin.ModelAdmin):
    list_display = ['nombre_cliente', 'cedula_cliente', 'telefono_cliente', 'evento', 'vendedor', 'estado', 'fecha_visita']
    list_filter = ['estado', 'invitacion__evento', 'fecha_visita', 'invitacion__vendedor']
    search_fields = ['nombre_cliente', 'cedula_cliente', 'telefono_cliente', 'email_cliente']
    readonly_fields = ['fecha_visita', 'evento', 'vendedor']
    
    fieldsets = (
        ('Información del Cliente', {
            'fields': ('nombre_cliente', 'cedula_cliente', 'telefono_cliente', 'email_cliente')
        }),
        ('Información del Evento', {
            'fields': ('invitacion', 'evento', 'vendedor'),
        }),
        ('Estado y Seguimiento', {
            'fields': ('estado', 'observaciones', 'registrado_por')
        }),
        ('Auditoría', {
            'fields': ('fecha_visita',),
            'classes': ('collapse',)
        })
    )
    
    def evento(self, obj):
        return obj.invitacion.evento.nombre
    evento.short_description = 'Evento'
    
    def vendedor(self, obj):
        return obj.invitacion.vendedor.get_full_name() or obj.invitacion.vendedor.username
    vendedor.short_description = 'Vendedor'


@admin.register(EstadisticaEvento)
class EstadisticaEventoAdmin(admin.ModelAdmin):
    list_display = ['evento', 'total_invitaciones', 'total_visitas', 'total_clientes_unicos', 'fecha_actualizacion']
    readonly_fields = ['total_invitaciones', 'total_visitas', 'total_clientes_unicos', 'estadisticas_vendedores', 'fecha_actualizacion']
    
    actions = ['actualizar_estadisticas']
    
    def actualizar_estadisticas(self, request, queryset):
        for estadistica in queryset:
            estadistica.actualizar_estadisticas()
        self.message_user(request, f'{queryset.count()} estadísticas actualizadas correctamente.')
    actualizar_estadisticas.short_description = 'Actualizar estadísticas seleccionadas'