#!/usr/bin/env python
"""
Script para crear los roles personalizados: Ventas y Registro
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.accounts.models import MenuCategory, User, Role, Navigation
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def create_ventas_role():
    """Crear rol Ventas con acceso solo al perfil"""
    print("👤 Creando rol Ventas...")
    
    # Crear o obtener rol de Ventas
    ventas_role, created = Role.objects.get_or_create(
        name='Ventas',
        defaults={
            'description': 'Rol de ventas con acceso limitado solo al perfil de usuario',
            'is_system': False,
            'is_active': True
        }
    )
    
    # Obtener módulos relacionados con perfil
    profile_modules = []
    try:
        # Buscar módulos relacionados con perfil - solo acceso básico
        profile_group = Group.objects.get(name='Usuarios')
        profile_modules.append(profile_group)
    except Group.DoesNotExist:
        print("  ⚠️  Módulo 'Usuarios' no encontrado para rol Ventas")
    
    # Limpiar grupos existentes y asignar solo módulos de perfil
    ventas_role.groups.clear()
    for module in profile_modules:
        ventas_role.groups.add(module)
    
    status = "✅ Creado" if created else "ℹ️  Ya existe (actualizado)"
    print(f"  {status}: {ventas_role.name}")
    print(f"  📦 Módulos asignados: {ventas_role.groups.count()}")
    
    return ventas_role

def create_registro_role():
    """Crear rol Registro con acceso al perfil, gestión de equipos y jerarquía"""
    print("🏢 Creando rol Registro...")
    
    # Crear o obtener rol de Registro
    registro_role, created = Role.objects.get_or_create(
        name='Registro',
        defaults={
            'description': 'Rol de registro con acceso al perfil, gestión de equipos y jerarquía de equipos',
            'is_system': False,
            'is_active': True
        }
    )
    
    # Obtener módulos relacionados
    assigned_modules = []
    
    # Módulos a asignar para el rol Registro
    module_names = [
        'Usuarios',             # Para ver perfil
        'Gestión de Equipos',   # Para gestión de equipos
        'Jerarquía de Equipos', # Para jerarquía de equipos
        'Dashboard de Ventas',  # Para acceso básico a información de ventas
    ]
    
    for module_name in module_names:
        try:
            module = Group.objects.get(name=module_name)
            assigned_modules.append(module)
        except Group.DoesNotExist:
            print(f"  ⚠️  Módulo '{module_name}' no encontrado, omitiendo...")
            continue
    
    # Limpiar grupos existentes y asignar módulos específicos
    registro_role.groups.clear()
    for module in assigned_modules:
        registro_role.groups.add(module)
    
    status = "✅ Creado" if created else "ℹ️  Ya existe (actualizado)"
    print(f"  {status}: {registro_role.name}")
    print(f"  📦 Módulos asignados: {registro_role.groups.count()}")
    
    return registro_role

def create_custom_permissions():
    """Crear permisos específicos para los nuevos roles"""
    print("🔒 Creando permisos específicos...")
    
    try:
        user_ct = ContentType.objects.get_for_model(User)
        
        custom_permissions = [
            # Permisos para rol Ventas
            {
                'codename': 'can_view_own_profile',
                'name': 'Puede ver su propio perfil',
                'content_type': user_ct
            },
            {
                'codename': 'can_edit_own_profile',
                'name': 'Puede editar su propio perfil',
                'content_type': user_ct
            },
            
            # Permisos para rol Registro
            {
                'codename': 'can_manage_sales_team',
                'name': 'Puede gestionar equipo de ventas',
                'content_type': user_ct
            },
            {
                'codename': 'can_view_team_hierarchy',
                'name': 'Puede ver jerarquía de equipos',
                'content_type': user_ct
            },
            {
                'codename': 'can_manage_team_members',
                'name': 'Puede gestionar miembros del equipo',
                'content_type': user_ct
            }
        ]
        
        created_permissions = []
        for perm_data in custom_permissions:
            permission, created = Permission.objects.get_or_create(
                codename=perm_data['codename'],
                content_type=perm_data['content_type'],
                defaults={'name': perm_data['name']}
            )
            created_permissions.append(permission)
            status = "✅ Creado" if created else "ℹ️  Ya existe"
            print(f"  {status}: {permission.name}")
        
        return created_permissions
        
    except Exception as e:
        print(f"  ❌ Error creando permisos: {e}")
        return []

def assign_permissions_to_roles(ventas_role, registro_role, permissions):
    """Asignar permisos específicos a cada rol"""
    print("🔑 Asignando permisos a roles...")
    
    # Permisos para rol Ventas
    ventas_permissions = [
        'can_view_own_profile',
        'can_edit_own_profile',
    ]
    
    # Permisos para rol Registro  
    registro_permissions = [
        'can_view_own_profile',
        'can_edit_own_profile',
        'can_manage_sales_team',
        'can_view_team_hierarchy',
        'can_manage_team_members',
    ]
    
    # Asignar permisos al rol Ventas
    for group in ventas_role.groups.all():
        for perm in permissions:
            if perm.codename in ventas_permissions:
                group.permissions.add(perm)
    
    print(f"  ✅ Permisos asignados al rol Ventas: {len(ventas_permissions)}")
    
    # Asignar permisos al rol Registro
    for group in registro_role.groups.all():
        for perm in permissions:
            if perm.codename in registro_permissions:
                group.permissions.add(perm)
    
    print(f"  ✅ Permisos asignados al rol Registro: {len(registro_permissions)}")

def create_team_leader_role():
    """Crear rol Team Leader (igual que Ventas por ahora)"""
    print("👥 Creando rol Team Leader...")
    
    team_leader_role, created = Role.objects.get_or_create(
        name='Team Leader',
        defaults={
            'description': 'Rol de team leader con acceso limitado al perfil de usuario',
            'is_system': False,
            'is_active': True
        }
    )
    
    # Obtener módulos (igual que Ventas)
    profile_modules = []
    try:
        profile_group = Group.objects.get(name='Usuarios')
        profile_modules.append(profile_group)
    except Group.DoesNotExist:
        print("  ⚠️  Módulo 'Usuarios' no encontrado para rol Team Leader")
    
    # Limpiar y asignar módulos
    team_leader_role.groups.clear()
    for module in profile_modules:
        team_leader_role.groups.add(module)
    
    status = "✅ Creado" if created else "ℹ️  Ya existe (actualizado)"
    print(f"  {status}: {team_leader_role.name}")
    print(f"  📦 Módulos asignados: {team_leader_role.groups.count()}")
    
    return team_leader_role

def create_jefe_equipo_role():
    """Crear rol Jefe de Equipo (igual que Ventas por ahora)"""
    print("🏆 Creando rol Jefe de Equipo...")
    
    jefe_equipo_role, created = Role.objects.get_or_create(
        name='Jefe de Equipo',
        defaults={
            'description': 'Rol de jefe de equipo con acceso limitado al perfil de usuario',
            'is_system': False,
            'is_active': True
        }
    )
    
    # Obtener módulos (igual que Ventas)
    profile_modules = []
    try:
        profile_group = Group.objects.get(name='Usuarios')
        profile_modules.append(profile_group)
    except Group.DoesNotExist:
        print("  ⚠️  Módulo 'Usuarios' no encontrado para rol Jefe de Equipo")
    
    # Limpiar y asignar módulos
    jefe_equipo_role.groups.clear()
    for module in profile_modules:
        jefe_equipo_role.groups.add(module)
    
    status = "✅ Creado" if created else "ℹ️  Ya existe (actualizado)"
    print(f"  {status}: {jefe_equipo_role.name}")
    print(f"  📦 Módulos asignados: {jefe_equipo_role.groups.count()}")
    
    return jefe_equipo_role

def create_gerente_proyecto_role():
    """Crear rol Gerente de Proyecto (igual que Ventas por ahora)"""
    print("🏗️ Creando rol Gerente de Proyecto...")
    
    gerente_proyecto_role, created = Role.objects.get_or_create(
        name='Gerente de Proyecto',
        defaults={
            'description': 'Rol de gerente de proyecto con acceso limitado al perfil de usuario',
            'is_system': False,
            'is_active': True
        }
    )
    
    # Obtener módulos (igual que Ventas)
    profile_modules = []
    try:
        profile_group = Group.objects.get(name='Usuarios')
        profile_modules.append(profile_group)
    except Group.DoesNotExist:
        print("  ⚠️  Módulo 'Usuarios' no encontrado para rol Gerente de Proyecto")
    
    # Limpiar y asignar módulos
    gerente_proyecto_role.groups.clear()
    for module in profile_modules:
        gerente_proyecto_role.groups.add(module)
    
    status = "✅ Creado" if created else "ℹ️  Ya existe (actualizado)"
    print(f"  {status}: {gerente_proyecto_role.name}")
    print(f"  📦 Módulos asignados: {gerente_proyecto_role.groups.count()}")
    
    return gerente_proyecto_role

def assign_permissions_to_all_roles(ventas_role, registro_role, team_leader_role, jefe_equipo_role, gerente_proyecto_role, permissions):
    """Asignar permisos específicos a todos los roles"""
    print("🔑 Asignando permisos a todos los roles...")
    
    # Permisos básicos para roles tipo Ventas
    basic_permissions = [
        'can_view_own_profile',
        'can_edit_own_profile',
    ]
    
    # Permisos avanzados para rol Registro  
    registro_permissions = [
        'can_view_own_profile',
        'can_edit_own_profile',
        'can_manage_sales_team',
        'can_view_team_hierarchy',
        'can_manage_team_members',
    ]
    
    # Asignar permisos básicos a roles tipo Ventas
    for role in [ventas_role, team_leader_role, jefe_equipo_role, gerente_proyecto_role]:
        for group in role.groups.all():
            for perm in permissions:
                if perm.codename in basic_permissions:
                    group.permissions.add(perm)
        print(f"  ✅ Permisos asignados al rol {role.name}: {len(basic_permissions)}")
    
    # Asignar permisos avanzados al rol Registro
    for group in registro_role.groups.all():
        for perm in permissions:
            if perm.codename in registro_permissions:
                group.permissions.add(perm)
    print(f"  ✅ Permisos asignados al rol Registro: {len(registro_permissions)}")
    
    # Asignar permisos específicos de Django para el rol Registro
    assign_django_permissions_to_registro(registro_role)

def assign_django_permissions_to_registro(registro_role):
    """Asignar permisos específicos de Django necesarios para las vistas de sales"""
    print("🎯 Asignando permisos específicos de Django al rol Registro...")
    
    # Permisos específicos que necesita el rol Registro basado en los decoradores @permission_required
    django_permissions_needed = [
        # Permisos de equipos de venta (equipos.py y jerarquia.py)
        'sales_team_management.view_equipoventa',
        'sales_team_management.add_equipoventa', 
        'sales_team_management.change_equipoventa',
        'sales_team_management.delete_equipoventa',
        
        # Permisos de gerente de equipo
        'sales_team_management.add_gerenteequipo',
        'sales_team_management.change_gerenteequipo',
        'sales_team_management.view_gerenteequipo',
        'sales_team_management.delete_gerenteequipo',
        
        # Permisos de jerarquía (jefe de venta, team leader, vendedor)
        'sales_team_management.view_jefeventa',
        'sales_team_management.add_jefeventa',
        'sales_team_management.change_jefeventa',
        'sales_team_management.delete_jefeventa',
        
        'sales_team_management.view_teamleader',
        'sales_team_management.add_teamleader',
        'sales_team_management.change_teamleader',
        'sales_team_management.delete_teamleader',
        
        'sales_team_management.view_vendedor',
        'sales_team_management.add_vendedor',
        'sales_team_management.change_vendedor',
        'sales_team_management.delete_vendedor',
        
        # Permisos de comisiones
        'sales_team_management.view_comisionventa',
        'sales_team_management.add_comisionventa',
        'sales_team_management.change_comisionventa',
        'sales_team_management.delete_comisionventa',
    ]
    
    permissions_added = 0
    
    for group in registro_role.groups.all():
        for perm_code in django_permissions_needed:
            try:
                app_label, codename = perm_code.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                group.permissions.add(permission)
                permissions_added += 1
                print(f"  ✅ Añadido: {perm_code}")
                
            except Permission.DoesNotExist:
                print(f"  ⚠️  Permiso no encontrado: {perm_code}")
            except Exception as e:
                print(f"  ❌ Error con {perm_code}: {e}")
    
    print(f"  🎉 Total permisos Django asignados: {permissions_added}")

def main():
    """Función principal del script"""
    print("🚀 Creando roles personalizados completos...")
    print("=" * 60)
    
    # 1. Crear permisos personalizados
    permissions = create_custom_permissions()
    print()
    
    # 2. Crear todos los roles
    ventas_role = create_ventas_role()
    print()
    
    team_leader_role = create_team_leader_role()
    print()
    
    jefe_equipo_role = create_jefe_equipo_role()
    print()
    
    gerente_proyecto_role = create_gerente_proyecto_role()
    print()
    
    registro_role = create_registro_role()
    print()
    
    # 3. Asignar permisos específicos a todos los roles
    assign_permissions_to_all_roles(
        ventas_role, registro_role, team_leader_role, 
        jefe_equipo_role, gerente_proyecto_role, permissions
    )
    print()
    
    # Resumen final
    print("=" * 60)
    print("🎉 Todos los roles creados exitosamente:")
    print()
    
    roles = [
        ("👤 Vendedor", ventas_role, "Solo visualización y edición del propio perfil"),
        ("👥 Team Leader", team_leader_role, "Solo visualización y edición del propio perfil"),
        ("🏆 Jefe de Equipo", jefe_equipo_role, "Solo visualización y edición del propio perfil"),
        ("🏗️ Gerente de Proyecto", gerente_proyecto_role, "Solo visualización y edición del propio perfil"),
        ("🏢 Registro", registro_role, "Perfil, gestión de equipos y jerarquía"),
    ]
    
    for icon_name, role, permissions_desc in roles:
        print(f"{icon_name}:")
        print(f"   • Descripción: {role.description}")
        print(f"   • Módulos asignados: {role.groups.count()}")
        print(f"   • Permisos: {permissions_desc}")
        print()
    
    print("✨ Los roles están listos para asignación automática!")
    print("💡 Próximo paso: Implementar asignación automática en modelos de jerarquía.")

if __name__ == "__main__":
    main()