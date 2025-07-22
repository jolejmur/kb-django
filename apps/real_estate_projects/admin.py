# apps/real_estate_projects/admin.py
from django.contrib import admin
from .models import (
    GerenteProyecto, JefeProyecto, Proyecto, AsignacionEquipoProyecto,
    Fase, Torre, Piso, Sector, Manzana, Inmueble, ComisionDesarrollo
)


@admin.register(GerenteProyecto)
class GerenteProyectoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'activo', 'created_at']
    list_filter = ['activo', 'created_at']
    search_fields = ['usuario__username', 'usuario__first_name', 'usuario__last_name']


@admin.register(JefeProyecto)
class JefeProyectoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'gerente_proyecto', 'activo', 'created_at']
    list_filter = ['activo', 'created_at']
    search_fields = ['usuario__username', 'usuario__first_name', 'usuario__last_name']


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'estado', 'activo']
    list_filter = ['tipo', 'estado', 'activo', 'created_at']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Fase)
class FaseAdmin(admin.ModelAdmin):
    list_display = ['proyecto', 'numero_fase', 'nombre', 'fecha_entrega_prevista', 'activo']
    list_filter = ['proyecto__tipo', 'activo', 'fecha_entrega_prevista']
    search_fields = ['proyecto__nombre', 'nombre']


@admin.register(Torre)
class TorreAdmin(admin.ModelAdmin):
    list_display = ['fase', 'numero_torre', 'nombre', 'numero_pisos', 'activo']
    list_filter = ['fase__proyecto', 'activo']
    search_fields = ['fase__proyecto__nombre', 'nombre']


@admin.register(Piso)
class PisoAdmin(admin.ModelAdmin):
    list_display = ['torre', 'numero_piso', 'nombre', 'activo']
    list_filter = ['torre__fase__proyecto', 'activo']


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ['fase', 'numero_sector', 'nombre', 'activo']
    list_filter = ['fase__proyecto', 'activo']
    search_fields = ['fase__proyecto__nombre', 'nombre']


@admin.register(Manzana)
class ManzanaAdmin(admin.ModelAdmin):
    list_display = ['sector', 'numero_manzana', 'nombre', 'activo']
    list_filter = ['sector__fase__proyecto', 'activo']


@admin.register(Inmueble)
class InmuebleAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'fase', 'tipo', 'estado', 'precio_venta', 'ubicacion_completa']
    list_filter = ['tipo', 'estado', 'fase__proyecto', 'disponible']
    search_fields = ['codigo', 'fase__proyecto__nombre']
    readonly_fields = ['ubicacion_completa', 'precio_por_m2']


@admin.register(ComisionDesarrollo)
class ComisionDesarrolloAdmin(admin.ModelAdmin):
    list_display = ['proyecto', 'porcentaje_gerente_proyecto', 'porcentaje_jefe_proyecto', 'activo']
    list_filter = ['activo', 'proyecto']
