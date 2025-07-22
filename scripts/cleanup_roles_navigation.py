#!/usr/bin/env python
"""
Script para limpiar datos de roles, navegación y categorías creados anteriormente
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.accounts.models import MenuCategory, Role, Navigation
from django.contrib.auth.models import Group

def cleanup_navigation():
    """Eliminar elementos de navegación"""
    print("🗑️  Eliminando elementos de navegación...")
    count = Navigation.objects.count()
    Navigation.objects.all().delete()
    print(f"  ✅ {count} elementos de navegación eliminados")

def cleanup_groups():
    """Eliminar grupos (módulos)"""
    print("🗑️  Eliminando grupos/módulos...")
    count = Group.objects.count()
    Group.objects.all().delete()
    print(f"  ✅ {count} grupos eliminados")

def cleanup_roles():
    """Eliminar roles (mantener superusuarios sin rol)"""
    print("🗑️  Eliminando roles...")
    # Desasignar rol de todos los usuarios antes de eliminar
    from apps.accounts.models import User
    User.objects.update(role=None)
    
    count = Role.objects.count()
    Role.objects.all().delete()
    print(f"  ✅ {count} roles eliminados")

def cleanup_categories():
    """Eliminar categorías del menú"""
    print("🗑️  Eliminando categorías del menú...")
    count = MenuCategory.objects.count()
    MenuCategory.objects.all().delete()
    print(f"  ✅ {count} categorías eliminadas")

def main():
    """Función principal de limpieza"""
    print("🧹 Limpiando datos de roles, navegación y categorías...")
    print("=" * 60)
    
    try:
        # Orden importante: eliminar desde las dependencias hacia arriba
        cleanup_navigation()
        cleanup_groups()
        cleanup_roles()
        cleanup_categories()
        
        print("=" * 60)
        print("✅ Limpieza completada exitosamente!")
        print("💡 Ahora puedes ejecutar setup_roles_permissions.py con datos limpios")
        
    except Exception as e:
        print(f"❌ Error durante la limpieza: {e}")
        print("⚠️  Es posible que algunos datos no se hayan eliminado correctamente")

if __name__ == "__main__":
    main()