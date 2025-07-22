#!/usr/bin/env python
"""
Script para sincronizar grupos de roles con usuarios.
Este script asigna los grupos del rol directamente al usuario para que Django
reconozca los permisos inmediatamente sin necesidad de override de has_perm.
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.accounts.models import User, Role
from django.contrib.auth.models import Group

def sync_role_groups_to_users():
    """Sincroniza los grupos de los roles con los usuarios"""
    print("🔄 Sincronizando grupos de roles con usuarios...")
    print("=" * 60)
    
    # Obtener todos los usuarios con rol asignado
    users_with_roles = User.objects.filter(role__isnull=False)
    
    if not users_with_roles.exists():
        print("ℹ️  No hay usuarios con roles asignados")
        return
    
    total_sync = 0
    
    for user in users_with_roles:
        print(f"\n👤 Usuario: {user.username}")
        print(f"   Rol: {user.role.name}")
        
        # Obtener grupos del rol
        role_groups = user.role.groups.all()
        print(f"   Grupos del rol: {role_groups.count()}")
        
        # Limpiar grupos actuales del usuario
        user.groups.clear()
        print("   ✅ Grupos anteriores limpiados")
        
        # Asignar grupos del rol al usuario
        groups_added = 0
        for group in role_groups:
            user.groups.add(group)
            groups_added += 1
            print(f"   ➕ Agregado: {group.name}")
        
        print(f"   ✅ Total grupos asignados: {groups_added}")
        total_sync += groups_added
        
        # Verificar un permiso específico como prueba
        test_perm = 'sales_team_management.view_equipoventa'
        has_perm = user.has_perm(test_perm)
        print(f"   🔍 Prueba permiso '{test_perm}': {has_perm}")
    
    print("\n" + "=" * 60)
    print(f"🎉 Sincronización completada!")
    print(f"📊 Usuarios procesados: {users_with_roles.count()}")
    print(f"📦 Total grupos sincronizados: {total_sync}")
    print("\n✨ Ahora todos los usuarios deberían tener acceso inmediato a sus módulos")

def main():
    """Función principal del script"""
    print("🚀 Script de sincronización de roles y grupos")
    print("Este script asigna los grupos del rol directamente a los usuarios")
    print("para que Django reconozca los permisos inmediatamente.\n")
    
    try:
        sync_role_groups_to_users()
    except Exception as e:
        print(f"\n❌ Error durante la sincronización: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())