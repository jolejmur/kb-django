#!/usr/bin/env python3
"""
Script para arreglar permisos de roles - asignar módulos a roles existentes
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/Users/jorgemucarcel/Desktop/kb-django-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth.models import Group
from apps.accounts.models import Role

def fix_role_permissions():
    """Asigna módulos apropiados a cada rol"""
    
    # Definir qué módulos debe tener cada rol
    ROLE_MODULES = {
        'Ventas': [
            'Dashboard de Ventas',
            'Gestión de Equipos',  # Solo lectura
            'Inmuebles en Venta',
            'Gestión de Leads',
            'Seguimiento Clientes',
        ],
        'Team Leader': [
            'Dashboard de Ventas',
            'Gestión de Equipos',
            'Jerarquía de Equipos',
            'Inmuebles en Venta',
            'Gestión de Leads',
            'Seguimiento Clientes',
            'Reportes de Ventas',
        ],
        'Jefe de Equipo': [
            'Dashboard de Ventas',
            'Gestión de Equipos',
            'Jerarquía de Equipos',
            'Comisiones de Venta',
            'Gestión de Proyectos Venta',
            'Inmuebles en Venta',
            'Dashboard CRM',
            'Gestión de Leads',
            'Seguimiento Clientes',
            'Reportes de Ventas',
            'Analytics de Equipos',
        ],
        'Gerente de Proyecto': [
            'Dashboard Proyectos',
            'Gestión de Proyectos',
            'Gestión de Inmuebles',
            'Ponderadores',
            'Dashboard de Ventas',
            'Gestión de Equipos',
            'Jerarquía de Equipos',
            'Comisiones de Venta',
            'Gestión de Proyectos Venta',
            'Inmuebles en Venta',
            'Dashboard CRM',
            'Reportes de Ventas',
            'Reportes de Proyectos',
            'Analytics de Equipos',
        ],
        'Registro': [
            'Gestión de Equipos',
            'Jerarquía de Equipos',
            'Gestión de Usuarios',  # Para poder crear usuarios
        ]
    }
    
    print("🔧 Arreglando permisos de roles...")
    
    for role_name, module_names in ROLE_MODULES.items():
        try:
            role = Role.objects.get(name=role_name)
            print(f"\n📋 Configurando rol: {role_name}")
            
            # Limpiar módulos actuales
            role.groups.clear()
            
            # Asignar nuevos módulos
            modules_assigned = 0
            for module_name in module_names:
                try:
                    group = Group.objects.get(name=module_name)
                    role.groups.add(group)
                    modules_assigned += 1
                    print(f"  ✅ {module_name}")
                except Group.DoesNotExist:
                    print(f"  ❌ Módulo no encontrado: {module_name}")
            
            print(f"  📊 Total módulos asignados: {modules_assigned}/{len(module_names)}")
            
        except Role.DoesNotExist:
            print(f"❌ Rol no encontrado: {role_name}")
    
    print("\n🎯 Verificando asignaciones...")
    for role in Role.objects.all():
        modules_count = role.groups.count()
        print(f"Rol: {role.name} | Módulos: {modules_count}")
        if modules_count == 0 and role.name != 'Super Admin':
            print(f"  ⚠️  {role.name} no tiene módulos asignados")

if __name__ == '__main__':
    fix_role_permissions()
    print("\n✅ ¡Permisos de roles arreglados!")