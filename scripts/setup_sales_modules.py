#!/usr/bin/env python
"""
Script para crear módulos de Gestión de Equipos de Venta en el sidebar
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.accounts.models import MenuCategory, User, Role, Navigation
from django.contrib.auth.models import Group

def main():
    print("👥 Configurando módulos de Gestión de Equipos de Venta...")
    
    # Crear categoría para Sales Team Management
    category, created = MenuCategory.objects.get_or_create(
        name='Gestión de Equipos',
        defaults={
            'description': 'Gestión de equipos de venta y comisiones',
            'icon': 'fas fa-users',
            'color': 'success',
            'order': 2,
            'is_active': True
        }
    )
    
    if created:
        print(f"✅ Categoría creada: {category.name}")
    else:
        print(f"ℹ️  Categoría ya existe: {category.name}")
    
    # Crear grupos/módulos para Sales Team Management
    modules = [
        {
            'name': 'Dashboard Ventas',
            'url': '/sales/',
            'icon': 'fas fa-chart-bar',
            'order': 1
        },
        {
            'name': 'Equipos de Venta',
            'url': '/sales/equipos/',
            'icon': 'fas fa-users',
            'order': 2
        },
        {
            'name': 'Jerarquía de Equipos',
            'url': '/sales/jerarquia/',
            'icon': 'fas fa-sitemap',
            'order': 3
        },
        {
            'name': 'Gestión de Comisiones',
            'url': '/sales/comisiones/',
            'icon': 'fas fa-percentage',
            'order': 4
        },
        {
            'name': 'Proyectos de Ventas',
            'url': '/sales/proyectos/',
            'icon': 'fas fa-briefcase',
            'order': 5
        }
    ]
    
    created_groups = []
    for module_data in modules:
        # Crear grupo
        group, group_created = Group.objects.get_or_create(
            name=module_data['name']
        )
        
        # Crear navegación
        navigation, nav_created = Navigation.objects.get_or_create(
            group=group,
            defaults={
                'name': module_data['name'],
                'url': module_data['url'],
                'icon': module_data['icon'],
                'order': module_data['order'],
                'category': category,
                'is_active': True
            }
        )
        
        created_groups.append(group)
        status = "✅ Creado" if group_created else "ℹ️  Ya existe"
        print(f"{status}: {module_data['name']}")
    
    # Crear o obtener rol de Super Admin
    super_admin_role, role_created = Role.objects.get_or_create(
        name='Super Admin',
        defaults={
            'description': 'Rol de super administrador con acceso completo',
            'is_active': True,
            'is_system': True
        }
    )
    
    if role_created:
        print(f"✅ Rol creado: {super_admin_role.name}")
    else:
        print(f"ℹ️  Rol ya existe: {super_admin_role.name}")
    
    # Asignar todos los grupos de Sales Team Management al rol
    for group in created_groups:
        super_admin_role.groups.add(group)
    
    # Verificar si existe el usuario admin y asignar el rol
    try:
        admin_user = User.objects.get(username='admin')
        admin_user.role = super_admin_role
        admin_user.save()
        print(f"✅ Usuario admin asignado al rol: {super_admin_role.name}")
    except User.DoesNotExist:
        print("⚠️  Usuario admin no encontrado. Ejecuta primero el script de reset de base de datos.")
    
    print(f"\n🎉 Configuración completada:")
    print(f"   - Categoría: {category.name}")
    print(f"   - Módulos creados: {len(created_groups)}")
    print(f"   - Rol: {super_admin_role.name}")
    print(f"   - Total grupos asignados al rol: {super_admin_role.groups.count()}")

if __name__ == "__main__":
    main()