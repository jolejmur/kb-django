#!/usr/bin/env python
"""
Script DEFINITIVO para resetear DB y crear módulos estáticos
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

def reset_database():
    """Elimina y recrea la base de datos"""
    print("🔄 Reseteando base de datos...")
    
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_file = os.path.join(project_dir, 'db.sqlite3')
    
    # Eliminar DB si existe
    if os.path.exists(db_file):
        os.remove(db_file)
        print("✅ Base de datos eliminada")
    
    # Configurar Django DESPUÉS de eliminar la DB
    django.setup()
    
    # Limpiar cache de Django ORM
    from django.core.cache import cache
    cache.clear()
    
    from django.core.management import execute_from_command_line
    original_argv = sys.argv[:]
    
    try:
        # Ejecutar migraciones
        sys.argv = ['manage.py', 'migrate']
        execute_from_command_line(sys.argv)
        print("✅ Migraciones aplicadas")
        
    except Exception as e:
        print(f"❌ Error en migraciones: {e}")
        sys.exit(1)
    finally:
        sys.argv = original_argv

def create_superuser():
    """Crear usuario admin"""
    print("👤 Creando superusuario...")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@korban.com',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        }
    )
    
    admin_user.set_password('admin123')
    admin_user.save()
    
    status = "✅ Superusuario creado" if created else "✅ Superusuario actualizado"
    print(f"{status}: admin/admin123")
    
    return admin_user

def create_static_modules():
    """Crear módulos ESTÁTICOS del sistema"""
    print("📦 Creando módulos estáticos...")
    
    from apps.accounts.models import MenuCategory, Navigation, Role
    from django.contrib.auth.models import Group
    
    # 1. CREAR CATEGORÍAS ESTÁTICAS
    categories_data = [
        {
            'name': 'Administración',
            'description': 'Módulos de administración del sistema',
            'icon': 'fas fa-cog',
            'color': 'danger',
            'order': 1,
            'is_system': True
        },
        {
            'name': 'Gestión de Usuarios',
            'description': 'Control de usuarios y accesos',
            'icon': 'fas fa-users',
            'color': 'info',
            'order': 2,
            'is_system': True
        },
        {
            'name': 'Proyectos Inmobiliarios',
            'description': 'Gestión de proyectos inmobiliarios',
            'icon': 'fas fa-building',
            'color': 'primary',
            'order': 3
        },
        {
            'name': 'Equipos de Venta',
            'description': 'Gestión de equipos y jerarquías de venta',
            'icon': 'fas fa-users-cog',
            'color': 'success',
            'order': 4
        },
        {
            'name': 'CRM y Leads',
            'description': 'Gestión de leads y comunicación con clientes',
            'icon': 'fas fa-handshake',
            'color': 'warning',
            'order': 5
        },
        {
            'name': 'Reportes y Analytics',
            'description': 'Reportes y estadísticas del sistema',
            'icon': 'fas fa-chart-bar',
            'color': 'purple',
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
        status = "✅ Creada" if created else "ℹ️  Ya existe"
        print(f"  {status}: {category.name}")
    
    # 2. CREAR MÓDULOS ESTÁTICOS
    modules_data = [
        # ===== ADMINISTRACIÓN =====
        {
            'category': 'Administración',
            'name': 'Dashboard Admin',
            'url': '/admin/dashboard/',
            'icon': 'fas fa-tachometer-alt',
            'order': 1
        },
        {
            'category': 'Administración',
            'name': 'Configuración Sistema',
            'url': '/admin/',
            'icon': 'fas fa-server',
            'order': 2
        },
        
        # ===== GESTIÓN DE USUARIOS =====
        {
            'category': 'Gestión de Usuarios',
            'name': 'Usuarios',
            'url': '/accounts/users/',
            'icon': 'fas fa-user',
            'order': 1
        },
        {
            'category': 'Gestión de Usuarios',
            'name': 'Roles y Permisos',
            'url': '/accounts/roles/',
            'icon': 'fas fa-shield-alt',
            'order': 2
        },
        {
            'category': 'Gestión de Usuarios',
            'name': 'Módulos del Sistema',
            'url': '/accounts/groups/',
            'icon': 'fas fa-cubes',
            'order': 3
        },
        
        # ===== PROYECTOS INMOBILIARIOS =====
        {
            'category': 'Proyectos Inmobiliarios',
            'name': 'Dashboard Proyectos',
            'url': '/projects/dashboard/',
            'icon': 'fas fa-chart-line',
            'order': 1
        },
        {
            'category': 'Proyectos Inmobiliarios',
            'name': 'Gestión de Proyectos',
            'url': '/projects/',
            'icon': 'fas fa-building',
            'order': 2
        },
        {
            'category': 'Proyectos Inmobiliarios',
            'name': 'Gestión de Inmuebles',
            'url': '/projects/inmuebles/',
            'icon': 'fas fa-home',
            'order': 3
        },
        {
            'category': 'Proyectos Inmobiliarios',
            'name': 'Ponderadores',
            'url': '/projects/ponderadores/',
            'icon': 'fas fa-weight',
            'order': 4
        },
        
        # ===== EQUIPOS DE VENTA =====
        {
            'category': 'Equipos de Venta',
            'name': 'Dashboard de Ventas',
            'url': '/sales/',
            'icon': 'fas fa-chart-area',
            'order': 1
        },
        {
            'category': 'Equipos de Venta',
            'name': 'Gestión de Equipos',
            'url': '/sales/equipos/',
            'icon': 'fas fa-users',
            'order': 2
        },
        {
            'category': 'Equipos de Venta',
            'name': 'Jerarquía de Equipos',
            'url': '/sales/jerarquia/',
            'icon': 'fas fa-sitemap',
            'order': 3
        },
        {
            'category': 'Equipos de Venta',
            'name': 'Comisiones de Venta',
            'url': '/sales/comisiones/',
            'icon': 'fas fa-percentage',
            'order': 4
        },
        {
            'category': 'Equipos de Venta',
            'name': 'Gestión de Proyectos Venta',
            'url': '/sales/proyectos/',
            'icon': 'fas fa-building',
            'order': 5
        },
        {
            'category': 'Equipos de Venta',
            'name': 'Inmuebles en Venta',
            'url': '/sales/inmuebles/',
            'icon': 'fas fa-home',
            'order': 6
        },
        
        # ===== CRM Y LEADS =====
        {
            'category': 'CRM y Leads',
            'name': 'Dashboard CRM',
            'url': '/crm/dashboard/',
            'icon': 'fas fa-handshake',
            'order': 1
        },
        {
            'category': 'CRM y Leads',
            'name': 'WhatsApp Business',
            'url': '/marketing/',
            'icon': 'fab fa-whatsapp',
            'order': 2
        },
        {
            'category': 'CRM y Leads',
            'name': 'Configuraciones de Meta Business',
            'url': '/marketing/configuracion/',
            'icon': 'fab fa-meta',
            'order': 3
        },
        {
            'category': 'CRM y Leads',
            'name': 'Supervisión de Chat',
            'url': '/marketing/supervision-chat/',
            'icon': 'fas fa-comments',
            'order': 4
        },
        {
            'category': 'CRM y Leads',
            'name': 'Gestión de Leads',
            'url': '/leads/',
            'icon': 'fas fa-user-plus',
            'order': 5
        },
        {
            'category': 'CRM y Leads',
            'name': 'Seguimiento Clientes',
            'url': '/crm/seguimiento/',
            'icon': 'fas fa-eye',
            'order': 6
        },
        
        # ===== REPORTES Y ANALYTICS =====
        {
            'category': 'Reportes y Analytics',
            'name': 'Dashboard de Reportes',
            'url': '/reports/dashboard/',
            'icon': 'fas fa-chart-bar',
            'order': 1
        },
        {
            'category': 'Reportes y Analytics',
            'name': 'Reportes de Ventas',
            'url': '/reports/ventas/',
            'icon': 'fas fa-chart-pie',
            'order': 2
        },
        {
            'category': 'Reportes y Analytics',
            'name': 'Reportes de Proyectos',
            'url': '/reports/proyectos/',
            'icon': 'fas fa-building',
            'order': 3
        },
        {
            'category': 'Reportes y Analytics',
            'name': 'Analytics de Equipos',
            'url': '/reports/equipos/',
            'icon': 'fas fa-users-cog',
            'order': 4
        },
        {
            'category': 'Reportes y Analytics',
            'name': 'Reportes CRM',
            'url': '/reports/crm/',
            'icon': 'fas fa-handshake',
            'order': 5
        },
        {
            'category': 'Reportes y Analytics',
            'name': 'Exportar Datos',
            'url': '/reports/export/',
            'icon': 'fas fa-download',
            'order': 6
        }
    ]
    
    created_groups = []
    for module_data in modules_data:
        # Crear grupo
        group, group_created = Group.objects.get_or_create(
            name=module_data['name']
        )
        created_groups.append(group)
        
        # Crear navegación
        category = created_categories[module_data['category']]
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
        
        status = "✅ Creado" if group_created else "ℹ️  Ya existe"
        print(f"  {status}: {module_data['category']} - {module_data['name']}")
    
    return created_groups

def create_super_admin_role(groups, admin_user):
    """Crear UN SOLO rol Super Admin con TODOS los módulos"""
    print("👥 Creando rol Super Admin ÚNICO...")
    
    from apps.accounts.models import Role
    
    # VERIFICAR que no existe ningún rol
    existing_roles = Role.objects.count()
    print(f"  📊 Roles existentes antes: {existing_roles}")
    
    # Si hay roles, eliminarlos
    if existing_roles > 0:
        Role.objects.all().delete()
        print(f"  🧹 {existing_roles} roles eliminados")
    
    # ASEGURAR que no hay roles
    remaining_roles = Role.objects.count()
    if remaining_roles > 0:
        print(f"  ❌ ERROR: Aún quedan {remaining_roles} roles")
        sys.exit(1)
    
    # Crear UN SOLO rol Super Admin
    super_admin_role = Role.objects.create(
        name='Super Admin',
        description='Administrador con acceso completo a todos los módulos estáticos',
        is_system=True,
        is_active=True
    )
    
    # VERIFICAR que solo se creó uno
    total_roles = Role.objects.count()
    if total_roles != 1:
        print(f"  ❌ ERROR: Se crearon {total_roles} roles en lugar de 1")
        sys.exit(1)
    
    # Asignar TODOS los grupos al rol
    for group in groups:
        super_admin_role.groups.add(group)
    
    # Asignar rol al usuario admin
    admin_user.role = super_admin_role
    admin_user.save()
    
    print(f"  ✅ ÚNICO rol creado: {super_admin_role.name} (ID: {super_admin_role.id})")
    print(f"  📦 Módulos asignados: {super_admin_role.groups.count()}")
    print(f"  👤 Usuario admin asignado al rol")
    print(f"  🔍 Total de roles en BD: {Role.objects.count()}")
    
    return super_admin_role

def main():
    """Función principal"""
    print("🚀 RESET DEFINITIVO DE BASE DE DATOS Y MÓDULOS ESTÁTICOS")
    print("=" * 60)
    
    try:
        # 1. Reset de base de datos
        reset_database()
        print()
        
        # 2. Crear superusuario
        admin_user = create_superuser()
        print()
        
        # 3. Crear módulos estáticos
        groups = create_static_modules()
        print()
        
        # 4. Crear rol Super Admin con todos los módulos
        super_admin_role = create_super_admin_role(groups, admin_user)
        print()
        
        # Resumen final
        print("=" * 60)
        print("🎉 CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
        print(f"   📁 Categorías: 6")
        print(f"   📦 Módulos estáticos: {len(groups)}")
        print(f"   👥 Rol Super Admin: ✅ ({super_admin_role.groups.count()} módulos)")
        print(f"   👤 Usuario admin: ✅ (rol asignado)")
        print()
        
        print("📋 CATEGORÍAS CREADAS:")
        print("   🔧 Administración (2 módulos)")
        print("   👥 Gestión de Usuarios (3 módulos)")  
        print("   🏢 Proyectos Inmobiliarios (4 módulos)")
        print("   💼 Equipos de Venta (6 módulos)")
        print("   📞 CRM y Leads (6 módulos)")
        print("   📊 Reportes y Analytics (6 módulos)")
        print()
        
        print("🔑 CREDENCIALES:")
        print("   - Usuario: admin")
        print("   - Contraseña: admin123")
        print("   - URL: http://127.0.0.1:8000/accounts/login/")
        print()
        
        print("✨ ¡Sistema completo listo para usar!")
        print("🚀 Sidebar con todas las funcionalidades de gestión de equipos y leads")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()