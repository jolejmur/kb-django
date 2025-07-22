#!/usr/bin/env python
"""
Script para limpiar todos los proyectos e inmuebles durante desarrollo
USO: python limpiar_proyectos.py

ADVERTENCIA: Este script eliminará TODOS los datos de proyectos inmobiliarios
"""

import os
import sys
import django

# Agregar el directorio padre al path para encontrar los módulos
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)

# Cambiar al directorio del proyecto
os.chdir(project_dir)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.real_estate_projects.models import (
    Proyecto, Fase, Torre, Piso, Sector, Manzana, Inmueble,
    GerenteProyecto, JefeProyecto, Ponderador, AsignacionEquipoProyecto
)

def confirmar_eliminacion():
    """Confirmar que el usuario realmente quiere eliminar todo"""
    print("⚠️  ADVERTENCIA: Este script eliminará TODOS los datos de proyectos inmobiliarios")
    print("\nEsto incluye:")
    print("- Todos los proyectos")
    print("- Todas las fases")
    print("- Todos los inmuebles")
    print("- Todos los ponderadores")
    print("- Todas las torres, pisos, sectores, manzanas")
    print("- Todos los gerentes y jefes de proyecto")
    print("- Todas las asignaciones de equipos")
    
    respuesta = input("\n¿Estás seguro de que quieres continuar? (escribe 'SI ELIMINAR TODO'): ")
    return respuesta.strip() == "SI ELIMINAR TODO"

def mostrar_estadisticas_antes():
    """Mostrar qué hay actualmente en la base de datos"""
    print("\n📊 ESTADÍSTICAS ACTUALES:")
    print(f"- Proyectos: {Proyecto.objects.count()}")
    print(f"- Fases: {Fase.objects.count()}")
    print(f"- Inmuebles: {Inmueble.objects.count()}")
    print(f"- Ponderadores: {Ponderador.objects.count()}")
    print(f"- Torres: {Torre.objects.count()}")
    print(f"- Pisos: {Piso.objects.count()}")
    print(f"- Sectores: {Sector.objects.count()}")
    print(f"- Manzanas: {Manzana.objects.count()}")
    print(f"- Gerentes de Proyecto: {GerenteProyecto.objects.count()}")
    print(f"- Jefes de Proyecto: {JefeProyecto.objects.count()}")
    print(f"- Asignaciones de Equipos: {AsignacionEquipoProyecto.objects.count()}")

def limpiar_todo():
    """Eliminar todos los datos en el orden correcto"""
    print("\n🧹 INICIANDO LIMPIEZA...")
    
    # Contador de eliminaciones
    total_eliminado = 0
    
    # 1. Eliminar asignaciones de equipos (relaciones many-to-many)
    count = AsignacionEquipoProyecto.objects.count()
    AsignacionEquipoProyecto.objects.all().delete()
    print(f"✓ Eliminadas {count} asignaciones de equipos")
    total_eliminado += count
    
    # 2. Eliminar inmuebles (tienen relaciones con ponderadores)
    count = Inmueble.objects.count()
    Inmueble.objects.all().delete()
    print(f"✓ Eliminados {count} inmuebles")
    total_eliminado += count
    
    # 3. Eliminar ponderadores
    count = Ponderador.objects.count()
    Ponderador.objects.all().delete()
    print(f"✓ Eliminados {count} ponderadores")
    total_eliminado += count
    
    # 4. Eliminar estructura de departamentos
    count_pisos = Piso.objects.count()
    Piso.objects.all().delete()
    print(f"✓ Eliminados {count_pisos} pisos")
    total_eliminado += count_pisos
    
    count_torres = Torre.objects.count()
    Torre.objects.all().delete()
    print(f"✓ Eliminadas {count_torres} torres")
    total_eliminado += count_torres
    
    # 5. Eliminar estructura de terrenos
    count_manzanas = Manzana.objects.count()
    Manzana.objects.all().delete()
    print(f"✓ Eliminadas {count_manzanas} manzanas")
    total_eliminado += count_manzanas
    
    count_sectores = Sector.objects.count()
    Sector.objects.all().delete()
    print(f"✓ Eliminados {count_sectores} sectores")
    total_eliminado += count_sectores
    
    # 6. Eliminar fases
    count = Fase.objects.count()
    Fase.objects.all().delete()
    print(f"✓ Eliminadas {count} fases")
    total_eliminado += count
    
    # 7. Eliminar proyectos
    count = Proyecto.objects.count()
    Proyecto.objects.all().delete()
    print(f"✓ Eliminados {count} proyectos")
    total_eliminado += count
    
    # 8. Eliminar roles de proyecto
    count_jefes = JefeProyecto.objects.count()
    JefeProyecto.objects.all().delete()
    print(f"✓ Eliminados {count_jefes} jefes de proyecto")
    total_eliminado += count_jefes
    
    count_gerentes = GerenteProyecto.objects.count()
    GerenteProyecto.objects.all().delete()
    print(f"✓ Eliminados {count_gerentes} gerentes de proyecto")
    total_eliminado += count_gerentes
    
    return total_eliminado

def verificar_limpieza():
    """Verificar que todo se eliminó correctamente"""
    print("\n🔍 VERIFICANDO LIMPIEZA...")
    
    modelos = [
        ('Proyectos', Proyecto),
        ('Fases', Fase),
        ('Inmuebles', Inmueble),
        ('Ponderadores', Ponderador),
        ('Torres', Torre),
        ('Pisos', Piso),
        ('Sectores', Sector),
        ('Manzanas', Manzana),
        ('Gerentes', GerenteProyecto),
        ('Jefes', JefeProyecto),
        ('Asignaciones', AsignacionEquipoProyecto)
    ]
    
    todo_limpio = True
    for nombre, modelo in modelos:
        count = modelo.objects.count()
        if count == 0:
            print(f"✅ {nombre}: 0 registros")
        else:
            print(f"❌ {nombre}: {count} registros restantes")
            todo_limpio = False
    
    return todo_limpio

def main():
    print("🗑️  SCRIPT DE LIMPIEZA DE PROYECTOS INMOBILIARIOS")
    print("=" * 50)
    
    # Mostrar estadísticas actuales
    mostrar_estadisticas_antes()
    
    # Confirmar eliminación
    if not confirmar_eliminacion():
        print("\n❌ Operación cancelada por el usuario.")
        return
    
    try:
        # Realizar limpieza
        total_eliminado = limpiar_todo()
        
        # Verificar que todo se eliminó
        if verificar_limpieza():
            print(f"\n🎉 LIMPIEZA COMPLETADA EXITOSAMENTE")
            print(f"📈 Total de registros eliminados: {total_eliminado}")
            print("\n💡 Ahora puedes crear nuevos proyectos desde cero.")
        else:
            print(f"\n⚠️  LIMPIEZA PARCIAL - Algunos registros no se eliminaron")
            
    except Exception as e:
        print(f"\n❌ ERROR durante la limpieza: {str(e)}")
        print("💡 Puede que algunos registros tengan dependencias que impidan la eliminación.")

if __name__ == "__main__":
    main()