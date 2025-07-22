# apps/sales_team_management/admin.py
from django.contrib import admin
from .models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    ComisionVenta
)


# ============================================================
# INLINES
# ============================================================

class GerenteEquipoInline(admin.TabularInline):
    model = GerenteEquipo
    extra = 0
    fields = ('usuario', 'activo')


class JefeVentaInline(admin.TabularInline):
    model = JefeVenta
    extra = 0
    fields = ('usuario', 'activo')


class TeamLeaderInline(admin.TabularInline):
    model = TeamLeader
    extra = 0
    fields = ('usuario', 'activo')


class VendedorInline(admin.TabularInline):
    model = Vendedor
    extra = 0
    fields = ('usuario', 'activo')




# ============================================================
# ADMIN PARA EQUIPOS DE VENTA
# ============================================================

@admin.register(EquipoVenta)
class EquipoVentaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'total_vendedores', 'created_at')
    list_filter = ('activo', 'created_at')
    search_fields = ('nombre', 'descripcion')
    ordering = ('nombre',)
    inlines = [GerenteEquipoInline]

    def total_vendedores(self, obj):
        return obj.total_vendedores

    total_vendedores.short_description = 'Total Vendedores'


@admin.register(GerenteEquipo)
class GerenteEquipoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'equipo_venta', 'activo', 'created_at')
    list_filter = ('activo', 'equipo_venta', 'created_at')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'equipo_venta__nombre')
    inlines = [JefeVentaInline]


@admin.register(JefeVenta)
class JefeVentaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'gerente_equipo', 'activo', 'created_at')
    list_filter = ('activo', 'created_at')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    inlines = [TeamLeaderInline]


@admin.register(TeamLeader)
class TeamLeaderAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'jefe_venta', 'activo', 'created_at')
    list_filter = ('activo', 'created_at')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    inlines = [VendedorInline]


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'team_leader', 'activo', 'created_at')
    list_filter = ('activo', 'created_at')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')


# ============================================================
# ADMIN PARA COMISIONES DE VENTAS
# ============================================================

@admin.register(ComisionVenta)
class ComisionVentaAdmin(admin.ModelAdmin):
    list_display = (
        'equipo_venta', 'porcentaje_gerente_equipo',
        'porcentaje_jefe_venta', 'porcentaje_team_leader',
        'porcentaje_vendedor', 'total_porcentaje', 'activo', 'created_at'
    )
    list_filter = ('activo', 'created_at')
    search_fields = ('equipo_venta__nombre',)

    def total_porcentaje(self, obj):
        return f"{obj.total_porcentaje()}%"

    total_porcentaje.short_description = 'Total %'