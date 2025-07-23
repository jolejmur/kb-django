#!/usr/bin/env python3
"""
Script para crear roles con permisos automáticamente
Uso: python3 create_role_with_permissions.py
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

def create_role_with_modules(role_name, description, modules_list):
    """
    Crea un rol y le asigna módulos automáticamente
    
    Args:
        role_name (str): Nombre del rol
        description (str): Descripción del rol
        modules_list (list): Lista de nombres de módulos/grupos
    """
    print(f"🔧 Creando rol: {role_name}")
    
    # Crear o actualizar el rol
    role, created = Role.objects.get_or_create(
        name=role_name,
        defaults={
            'description': description,
            'is_active': True
        }
    )
    
    if created:
        print(f"✅ Nuevo rol creado: {role_name}")
    else:
        print(f"♻️  Rol existente actualizado: {role_name}")
        role.description = description
        role.save()
    
    # Limpiar módulos actuales
    role.groups.clear()
    
    # Asignar nuevos módulos
    print(f"📋 Asignando módulos...")
    total_permisos = 0
    modules_assigned = 0
    
    for module_name in modules_list:
        try:
            group = Group.objects.get(name=module_name)
            role.groups.add(group)
            permisos_count = group.permissions.count()
            total_permisos += permisos_count
            modules_assigned += 1
            print(f"  ✅ {module_name} ({permisos_count} permisos)")
        except Group.DoesNotExist:
            print(f"  ❌ Módulo no encontrado: {module_name}")
    
    print(f"📊 Resumen:")
    print(f"  - Módulos asignados: {modules_assigned}/{len(modules_list)}")
    print(f"  - Total permisos: {total_permisos}")
    print(f"  - Rol activo: {role.is_active}")
    
    return role

def list_available_modules():
    """Lista todos los módulos/grupos disponibles"""
    print("📋 MÓDULOS DISPONIBLES:")
    groups = Group.objects.all().order_by('name')
    for group in groups:
        print(f"  - {group.name} ({group.permissions.count()} permisos)")

if __name__ == '__main__':
    print("🎯 CREADOR DE ROLES CON PERMISOS AUTOMÁTICOS")
    print("=" * 50)
    
    # Ejemplo de uso: crear diferentes tipos de roles
    
    # 1. Rol de Auditor
    create_role_with_modules(
        role_name="Auditor",
        description="Rol para auditoría con acceso de solo lectura",
        modules_list=[
            "Dashboard de Ventas",
            "Gestión de Equipos", 
            "Jerarquía de Equipos",
            "Dashboard de Reportes",
            "Reportes de Ventas",
            "Analytics de Equipos"
        ]
    )
    
    print("\n" + "=" * 50)
    
    # 2. Rol de Coordinador
    create_role_with_modules(
        role_name="Coordinador",
        description="Rol intermedio para coordinación de equipos",
        modules_list=[
            "Dashboard de Ventas",
            "Gestión de Equipos",
            "Jerarquía de Equipos", 
            "Gestión de Leads",
            "Seguimiento Clientes",
            "Reportes de Ventas"
        ]
    )
    
    print("\n" + "=" * 50)
    list_available_modules()
    
    print("\n✅ ¡Roles creados exitosamente!")
    print("\n💡 INSTRUCCIONES PARA CREAR NUEVOS ROLES:")
    print("1. Llama a create_role_with_modules()")
    print("2. Especifica el nombre, descripción y lista de módulos")
    print("3. Los permisos se asignan automáticamente")
    print("4. No necesitas hacer 'carpintería' manual")