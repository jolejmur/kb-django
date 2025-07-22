#!/usr/bin/env python
"""
Script de configuración para PRODUCCIÓN - Django CRM
Configura la base de datos, módulos estáticos y roles personalizados
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_django():
    """Configurar Django según el entorno"""
    # Detectar entorno
    if os.getenv('PRODUCTION'):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
        print("🏭 Configurando para PRODUCCIÓN")
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
        print("🔧 Configurando para DESARROLLO")
    
    django.setup()

def apply_migrations():
    """Aplicar todas las migraciones"""
    print("📦 Aplicando migraciones...")
    
    from django.core.management import execute_from_command_line
    original_argv = sys.argv[:]
    
    try:
        # Ejecutar migraciones
        sys.argv = ['manage.py', 'migrate']
        execute_from_command_line(sys.argv)
        print("✅ Migraciones aplicadas correctamente")
        
    except Exception as e:
        print(f"❌ Error en migraciones: {e}")
        sys.exit(1)
    finally:
        sys.argv = original_argv

def create_superuser():
    """Crear usuario admin para producción"""
    print("👤 Configurando superusuario...")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Obtener credenciales desde variables de entorno o usar defaults
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@empresa.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    admin_user, created = User.objects.get_or_create(
        username=admin_username,
        defaults={
            'email': admin_email,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        }
    )
    
    admin_user.set_password(admin_password)
    admin_user.save()
    
    status = "✅ Superusuario creado" if created else "✅ Superusuario actualizado"
    print(f"{status}: {admin_username}")
    
    # Solo mostrar password en desarrollo
    if not os.getenv('PRODUCTION'):
        print(f"   Password: {admin_password}")
    
    return admin_user

def create_menu_categories():
    """Crear categorías de menú estáticas"""
    print("📂 Creando categorías de menú...")
    
    from apps.accounts.models import MenuCategory
    
    categories_data = [
        {
            'name': 'ADMINISTRACIÓN DEL SISTEMA',
            'description': 'Módulos de administración y configuración del sistema',
            'icon': 'fas fa-cogs',
            'color': 'red',
            'order': 1,
            'is_system': True
        },
        {
            'name': 'GESTIÓN DE USUARIOS',
            'description': 'Control de usuarios, roles y permisos',
            'icon': 'fas fa-users',
            'color': 'blue',
            'order': 2,
            'is_system': True
        },
        {
            'name': 'PROYECTOS INMOBILIARIOS',
            'description': 'Gestión de proyectos y propiedades inmobiliarias',
            'icon': 'fas fa-building',
            'color': 'green',
            'order': 3
        },
        {
            'name': 'EQUIPOS DE VENTA',
            'description': 'Gestión de equipos de venta y jerarquías',
            'icon': 'fas fa-users-cog',
            'color': 'orange',
            'order': 4
        },
        {
            'name': 'CRM Y COMUNICACIONES',
            'description': 'Gestión de clientes y comunicación WhatsApp',
            'icon': 'fas fa-handshake',
            'color': 'purple',
            'order': 5
        },
        {
            'name': 'REPORTES Y ANALYTICS',
            'description': 'Reportes, estadísticas y análisis de datos',
            'icon': 'fas fa-chart-bar',
            'color': 'indigo',
            'order': 6
        }
    ]
    
    created_categories = {}
    for cat_data in categories_data:
        category, created = MenuCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        created_categories[cat_data['name']] = category
        status = "✅ Creada" if created else "ℹ️  Actualizada"
        print(f"  {status}: {category.name}")
    
    return created_categories

def create_system_modules(categories):
    """Crear módulos del sistema"""
    print("📦 Creando módulos del sistema...")
    
    from apps.accounts.models import Navigation
    from django.contrib.auth.models import Group
    
    modules_data = [
        # ===== ADMINISTRACIÓN DEL SISTEMA =====
        {
            'category': 'ADMINISTRACIÓN DEL SISTEMA',
            'name': 'Dashboard Admin',
            'url': '/admin/',
            'icon': 'fas fa-tachometer-alt',
            'order': 1
        },
        {
            'category': 'ADMINISTRACIÓN DEL SISTEMA',
            'name': 'Configuración Sistema',
            'url': '/admin/auth/',
            'icon': 'fas fa-server',
            'order': 2
        },
        
        # ===== GESTIÓN DE USUARIOS =====
        {
            'category': 'GESTIÓN DE USUARIOS',
            'name': 'Usuarios',
            'url': '/accounts/users/',
            'icon': 'fas fa-user',
            'order': 1
        },
        {
            'category': 'GESTIÓN DE USUARIOS',
            'name': 'Roles y Permisos',
            'url': '/accounts/roles/',
            'icon': 'fas fa-shield-alt',
            'order': 2
        },
        {
            'category': 'GESTIÓN DE USUARIOS',
            'name': 'Módulos del Sistema',
            'url': '/accounts/groups/',
            'icon': 'fas fa-cubes',
            'order': 3
        },
        
        # ===== PROYECTOS INMOBILIARIOS =====
        {
            'category': 'PROYECTOS INMOBILIARIOS',
            'name': 'Dashboard Proyectos',
            'url': '/projects/',
            'icon': 'fas fa-chart-line',
            'order': 1
        },
        {
            'category': 'PROYECTOS INMOBILIARIOS',
            'name': 'Gestión de Proyectos',
            'url': '/projects/proyectos/',
            'icon': 'fas fa-building',
            'order': 2
        },
        {
            'category': 'PROYECTOS INMOBILIARIOS',
            'name': 'Gestión de Inmuebles',
            'url': '/projects/inmuebles/',
            'icon': 'fas fa-home',
            'order': 3
        },
        {
            'category': 'PROYECTOS INMOBILIARIOS',
            'name': 'Ponderadores',
            'url': '/projects/ponderadores/',
            'icon': 'fas fa-weight',
            'order': 4
        },
        
        # ===== EQUIPOS DE VENTA =====
        {
            'category': 'EQUIPOS DE VENTA',
            'name': 'Dashboard de Ventas',
            'url': '/sales/',
            'icon': 'fas fa-chart-area',
            'order': 1
        },
        {
            'category': 'EQUIPOS DE VENTA',
            'name': 'Gestión de Equipos',
            'url': '/sales/equipos/',
            'icon': 'fas fa-users',
            'order': 2
        },
        {
            'category': 'EQUIPOS DE VENTA',
            'name': 'Jerarquía de Equipos',
            'url': '/sales/jerarquia/',
            'icon': 'fas fa-sitemap',
            'order': 3
        },
        {
            'category': 'EQUIPOS DE VENTA',
            'name': 'Comisiones de Venta',
            'url': '/sales/comisiones/',
            'icon': 'fas fa-percentage',
            'order': 4
        },
        {
            'category': 'EQUIPOS DE VENTA',
            'name': 'Gestión de Proyectos Venta',
            'url': '/sales/proyectos/',
            'icon': 'fas fa-building',
            'order': 5
        },
        {
            'category': 'EQUIPOS DE VENTA',
            'name': 'Inmuebles en Venta',
            'url': '/sales/inmuebles/',
            'icon': 'fas fa-home',
            'order': 6
        },
        
        # ===== CRM Y COMUNICACIONES =====
        {
            'category': 'CRM Y COMUNICACIONES',
            'name': 'Dashboard CRM',
            'url': '/crm/',
            'icon': 'fas fa-handshake',
            'order': 1
        },
        {
            'category': 'CRM Y COMUNICACIONES',
            'name': 'WhatsApp Business',
            'url': '/marketing/',
            'icon': 'fab fa-whatsapp',
            'order': 2
        },
        {
            'category': 'CRM Y COMUNICACIONES',
            'name': 'Configuraciones de Meta Business',
            'url': '/marketing/configuracion/',
            'icon': 'fab fa-meta',
            'order': 3
        },
        {
            'category': 'CRM Y COMUNICACIONES',
            'name': 'Supervisión de Chat',
            'url': '/marketing/supervision-chat/',
            'icon': 'fas fa-comments',
            'order': 4
        },
        {
            'category': 'CRM Y COMUNICACIONES',
            'name': 'Gestión de Leads',
            'url': '/leads/',
            'icon': 'fas fa-user-plus',
            'order': 5
        },
        {
            'category': 'CRM Y COMUNICACIONES',
            'name': 'Seguimiento Clientes',
            'url': '/crm/seguimiento/',
            'icon': 'fas fa-eye',
            'order': 6
        },
        
        # ===== REPORTES Y ANALYTICS =====
        {
            'category': 'REPORTES Y ANALYTICS',
            'name': 'Dashboard de Reportes',
            'url': '/reports/',
            'icon': 'fas fa-chart-bar',
            'order': 1
        },
        {
            'category': 'REPORTES Y ANALYTICS',
            'name': 'Reportes de Ventas',
            'url': '/reports/ventas/',
            'icon': 'fas fa-chart-pie',
            'order': 2
        },
        {
            'category': 'REPORTES Y ANALYTICS',
            'name': 'Reportes de Proyectos',
            'url': '/reports/proyectos/',
            'icon': 'fas fa-building',
            'order': 3
        },
        {
            'category': 'REPORTES Y ANALYTICS',
            'name': 'Analytics de Equipos',
            'url': '/reports/equipos/',
            'icon': 'fas fa-users-cog',
            'order': 4
        },
        {
            'category': 'REPORTES Y ANALYTICS',
            'name': 'Reportes CRM',
            'url': '/reports/crm/',
            'icon': 'fas fa-handshake',
            'order': 5
        },
        {
            'category': 'REPORTES Y ANALYTICS',
            'name': 'Exportar Datos',
            'url': '/reports/export/',
            'icon': 'fas fa-download',
            'order': 6
        }
    ]
    
    created_groups = []
    for module_data in modules_data:
        # Crear grupo/módulo
        group, group_created = Group.objects.get_or_create(
            name=module_data['name']
        )
        created_groups.append(group)
        
        # Crear navegación
        category = categories[module_data['category']]
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
        
        # Actualizar navegación si ya existe
        if not nav_created:
            navigation.name = module_data['name']
            navigation.url = module_data['url']
            navigation.icon = module_data['icon']
            navigation.order = module_data['order']
            navigation.category = category
            navigation.save()
        
        status = "✅ Creado" if group_created else "ℹ️  Actualizado"
        print(f"  {status}: {module_data['name']}")
    
    return created_groups

def create_custom_roles(all_groups):
    """Crear roles personalizados del sistema"""
    print("👥 Creando roles personalizados...")
    
    from apps.accounts.models import Role
    from django.contrib.auth.models import Group
    
    # Obtener módulo de Usuarios (perfil básico)
    try:
        usuarios_module = Group.objects.get(name='Usuarios')
    except Group.DoesNotExist:
        print("  ❌ Error: Módulo 'Usuarios' no encontrado")
        return []
    
    # Obtener módulos para rol Registro
    registro_modules = []
    registro_module_names = ['Usuarios', 'Gestión de Equipos', 'Jerarquía de Equipos', 'Dashboard de Ventas']
    for module_name in registro_module_names:
        try:
            module = Group.objects.get(name=module_name)
            registro_modules.append(module)
        except Group.DoesNotExist:
            print(f"  ⚠️  Módulo '{module_name}' no encontrado para rol Registro")
    
    # Roles básicos (solo perfil)
    basic_roles_data = [
        {
            'name': 'Ventas',
            'description': 'Rol de vendedor con acceso limitado al perfil de usuario',
            'modules': [usuarios_module]
        },
        {
            'name': 'Team Leader',
            'description': 'Rol de team leader con acceso limitado al perfil de usuario',
            'modules': [usuarios_module]
        },
        {
            'name': 'Jefe de Equipo',
            'description': 'Rol de jefe de equipo con acceso limitado al perfil de usuario',
            'modules': [usuarios_module]
        },
        {
            'name': 'Gerente de Proyecto',
            'description': 'Rol de gerente de proyecto con acceso limitado al perfil de usuario',
            'modules': [usuarios_module]
        }
    ]
    
    # Rol especial Registro
    registro_role_data = {
        'name': 'Registro',
        'description': 'Rol de registro con acceso al perfil, gestión de equipos y jerarquía',
        'modules': registro_modules
    }
    
    # Crear Super Admin con todos los módulos
    super_admin_data = {
        'name': 'Super Admin',
        'description': 'Administrador con acceso completo a todos los módulos del sistema',
        'modules': all_groups,
        'is_system': True
    }
    
    created_roles = []
    
    # Crear roles básicos
    for role_data in basic_roles_data:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={
                'description': role_data['description'],
                'is_system': False,
                'is_active': True
            }
        )
        
        # Limpiar y asignar módulos
        role.groups.clear()
        for module in role_data['modules']:
            role.groups.add(module)
        
        created_roles.append(role)
        status = "✅ Creado" if created else "ℹ️  Actualizado"
        print(f"  {status}: {role.name} ({role.groups.count()} módulos)")
    
    # Crear rol Registro
    registro_role, created = Role.objects.get_or_create(
        name=registro_role_data['name'],
        defaults={
            'description': registro_role_data['description'],
            'is_system': False,
            'is_active': True
        }
    )
    
    # Limpiar y asignar módulos para Registro
    registro_role.groups.clear()
    for module in registro_role_data['modules']:
        registro_role.groups.add(module)
    
    created_roles.append(registro_role)
    status = "✅ Creado" if created else "ℹ️  Actualizado"
    print(f"  {status}: {registro_role.name} ({registro_role.groups.count()} módulos)")
    
    # Crear Super Admin
    super_admin_role, created = Role.objects.get_or_create(
        name=super_admin_data['name'],
        defaults={
            'description': super_admin_data['description'],
            'is_system': True,
            'is_active': True
        }
    )
    
    # Limpiar y asignar TODOS los módulos
    super_admin_role.groups.clear()
    for module in super_admin_data['modules']:
        super_admin_role.groups.add(module)
    
    created_roles.append(super_admin_role)
    status = "✅ Creado" if created else "ℹ️  Actualizado"
    print(f"  {status}: {super_admin_role.name} ({super_admin_role.groups.count()} módulos)")
    
    return created_roles, super_admin_role

def assign_permissions_to_roles():
    """Asignar permisos específicos de Django a los roles"""
    print("🔑 Asignando permisos específicos...")
    
    from apps.accounts.models import Role
    from django.contrib.auth.models import Permission
    
    try:
        registro_role = Role.objects.get(name='Registro')
        
        # Permisos específicos para rol Registro
        django_permissions_needed = [
            'sales_team_management.view_equipoventa',
            'sales_team_management.add_equipoventa', 
            'sales_team_management.change_equipoventa',
            'sales_team_management.delete_equipoventa',
            'sales_team_management.add_gerenteequipo',
            'sales_team_management.change_gerenteequipo',
            'sales_team_management.view_gerenteequipo',
            'sales_team_management.delete_gerenteequipo',
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
                    
                except Permission.DoesNotExist:
                    # Permiso no encontrado, continuar
                    pass
                except Exception as e:
                    print(f"  ⚠️  Error con {perm_code}: {e}")
        
        print(f"  ✅ Permisos asignados al rol Registro: {permissions_added}")
        
    except Role.DoesNotExist:
        print("  ⚠️  Rol Registro no encontrado, saltando asignación de permisos")

def sync_role_groups_to_users():
    """Sincronizar grupos de roles con usuarios existentes"""
    print("🔄 Sincronizando grupos de roles con usuarios...")
    
    from apps.accounts.models import User
    
    users_with_roles = User.objects.filter(role__isnull=False)
    
    if not users_with_roles.exists():
        print("  ℹ️  No hay usuarios con roles asignados")
        return
    
    synced_users = 0
    
    for user in users_with_roles:
        if user.role:
            # Limpiar grupos actuales
            user.groups.clear()
            
            # Asignar grupos del rol
            for group in user.role.groups.all():
                user.groups.add(group)
            
            synced_users += 1
    
    print(f"  ✅ Usuarios sincronizados: {synced_users}")

def assign_admin_role(admin_user, super_admin_role):
    """Asignar rol Super Admin al usuario administrador"""
    print("👑 Asignando rol Super Admin al administrador...")
    
    admin_user.role = super_admin_role
    admin_user.save()
    
    # Sincronizar grupos
    admin_user.groups.clear()
    for group in super_admin_role.groups.all():
        admin_user.groups.add(group)
    
    print(f"  ✅ Rol {super_admin_role.name} asignado a {admin_user.username}")

def collect_static_files():
    """Recopilar archivos estáticos para producción"""
    if os.getenv('PRODUCTION'):
        print("📁 Recopilando archivos estáticos...")
        
        from django.core.management import execute_from_command_line
        original_argv = sys.argv[:]
        
        try:
            sys.argv = ['manage.py', 'collectstatic', '--noinput']
            execute_from_command_line(sys.argv)
            print("✅ Archivos estáticos recopilados")
        except Exception as e:
            print(f"⚠️  Error recopilando estáticos: {e}")
        finally:
            sys.argv = original_argv

def main():
    """Función principal del script de configuración"""
    print("🚀 CONFIGURACIÓN DE PRODUCCIÓN - Django CRM")
    print("=" * 60)
    
    try:
        # 1. Configurar Django
        setup_django()
        print()
        
        # 2. Aplicar migraciones
        apply_migrations()
        print()
        
        # 3. Crear superusuario
        admin_user = create_superuser()
        print()
        
        # 4. Crear categorías de menú
        categories = create_menu_categories()
        print()
        
        # 5. Crear módulos del sistema
        all_groups = create_system_modules(categories)
        print()
        
        # 6. Crear roles personalizados
        created_roles, super_admin_role = create_custom_roles(all_groups)
        print()
        
        # 7. Asignar permisos específicos
        assign_permissions_to_roles()
        print()
        
        # 8. Asignar rol al administrador
        assign_admin_role(admin_user, super_admin_role)
        print()
        
        # 9. Sincronizar grupos de roles con usuarios
        sync_role_groups_to_users()
        print()
        
        # 10. Recopilar archivos estáticos (solo en producción)
        collect_static_files()
        print()
        
        # Resumen final
        print("=" * 60)
        print("🎉 CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
        print(f"   📂 Categorías creadas: {len(categories)}")
        print(f"   📦 Módulos del sistema: {len(all_groups)}")
        print(f"   👥 Roles creados: {len(created_roles)}")
        print(f"   👤 Administrador configurado: {admin_user.username}")
        print()
        
        print("📋 ROLES CREADOS:")
        for role in created_roles:
            print(f"   • {role.name}: {role.groups.count()} módulos")
        print()
        
        if not os.getenv('PRODUCTION'):
            print("🔑 CREDENCIALES DE DESARROLLO:")
            print(f"   Usuario: {admin_user.username}")
            print("   Contraseña: admin123")
            print("   URL: http://127.0.0.1:8000/accounts/login/")
            print()
        
        print("✨ ¡Sistema listo para usar!")
        print("📊 Dashboard con todos los módulos configurados")
        print("🔐 Roles y permisos asignados correctamente")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()