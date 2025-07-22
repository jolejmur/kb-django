#!/usr/bin/env python
"""
Script para crear roles, menú de navegación y permisos del sistema
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

def create_categories():
    """Crear categorías principales del menú"""
    print("📁 Creando categorías del menú...")
    
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
            'name': 'Proyectos',
            'description': 'Gestión de proyectos inmobiliarios',
            'icon': 'fas fa-building',
            'color': 'primary',
            'order': 3
        },
        {
            'name': 'Ventas',
            'description': 'Gestión de ventas y equipos comerciales',
            'icon': 'fas fa-handshake',
            'color': 'success',
            'order': 4
        },
        {
            'name': 'CRM',
            'description': 'Gestión de relaciones con clientes',
            'icon': 'fas fa-user-friends',
            'color': 'info',
            'order': 5
        },
        {
            'name': 'Reportes',
            'description': 'Reportes y analytics del sistema',
            'icon': 'fas fa-chart-bar',
            'color': 'success',
            'order': 6
        },
        {
            'name': 'Configuración',
            'description': 'Configuración del sistema',
            'icon': 'fas fa-tools',
            'color': 'warning',
            'order': 7
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
    
    return created_categories

def create_navigation_modules(categories):
    """Crear todos los módulos del sidebar organizados por categorías"""
    print("🧭 Creando todos los módulos del sidebar...")
    
    navigation_data = [
        # Administración del Sistema
        {
            'category': 'Administración',
            'name': 'Dashboard Admin',
            'url': '/admin/dashboard/',
            'icon': 'fas fa-tachometer-alt',
            'order': 1
        },
        {
            'category': 'Administración',
            'name': 'Configuración del Sistema',
            'url': '/admin/system/',
            'icon': 'fas fa-server',
            'order': 2
        },
        {
            'category': 'Administración',
            'name': 'Logs y Auditoría',
            'url': '/admin/logs/',
            'icon': 'fas fa-file-alt',
            'order': 3
        },
        {
            'category': 'Administración',
            'name': 'Base de Datos',
            'url': '/admin/database/',
            'icon': 'fas fa-database',
            'order': 4
        },
        {
            'category': 'Administración',
            'name': 'Backup y Restauración',
            'url': '/admin/backup/',
            'icon': 'fas fa-download',
            'order': 5
        },
        
        # Gestión de Usuarios y Accesos
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
            'name': 'Módulos',
            'url': '/accounts/groups/',
            'icon': 'fas fa-cubes',
            'order': 3
        },
        {
            'category': 'Gestión de Usuarios',
            'name': 'Perfiles de Usuario',
            'url': '/accounts/profiles/',
            'icon': 'fas fa-id-card',
            'order': 4
        },
        {
            'category': 'Gestión de Usuarios',
            'name': 'Sesiones Activas',
            'url': '/accounts/sessions/',
            'icon': 'fas fa-clock',
            'order': 5
        },
        
        # Proyectos Inmobiliarios
        {
            'category': 'Proyectos',
            'name': 'Dashboard Proyectos',
            'url': '/projects/dashboard/',
            'icon': 'fas fa-chart-line',
            'order': 1
        },
        {
            'category': 'Proyectos',
            'name': 'Gestión de Proyectos',
            'url': '/projects/',
            'icon': 'fas fa-building',
            'order': 2
        },
        {
            'category': 'Proyectos',
            'name': 'Gestión de Inmuebles',
            'url': '/projects/inmuebles/',
            'icon': 'fas fa-home',
            'order': 3
        },
        {
            'category': 'Proyectos',
            'name': 'Ponderadores',
            'url': '/projects/ponderadores/',
            'icon': 'fas fa-weight',
            'order': 4
        },
        {
            'category': 'Proyectos',
            'name': 'Tipos de Inmuebles',
            'url': '/projects/tipos/',
            'icon': 'fas fa-layer-group',
            'order': 5
        },
        {
            'category': 'Proyectos',
            'name': 'Estados de Proyectos',
            'url': '/projects/estados/',
            'icon': 'fas fa-tasks',
            'order': 6
        },
        {
            'category': 'Proyectos',
            'name': 'Ubicaciones',
            'url': '/projects/ubicaciones/',
            'icon': 'fas fa-map-marker-alt',
            'order': 7
        },
        
        # Gestión de Ventas
        {
            'category': 'Ventas',
            'name': 'Dashboard de Ventas',
            'url': '/sales/dashboard/',
            'icon': 'fas fa-chart-area',
            'order': 1
        },
        {
            'category': 'Ventas',
            'name': 'Equipo de Ventas',
            'url': '/sales/team/',
            'icon': 'fas fa-users',
            'order': 2
        },
        {
            'category': 'Ventas',
            'name': 'Clientes y Leads',
            'url': '/sales/clients/',
            'icon': 'fas fa-user-tie',
            'order': 3
        },
        {
            'category': 'Ventas',
            'name': 'Oportunidades',
            'url': '/sales/opportunities/',
            'icon': 'fas fa-bullseye',
            'order': 4
        },
        {
            'category': 'Ventas',
            'name': 'Contratos y Ventas',
            'url': '/sales/contracts/',
            'icon': 'fas fa-file-contract',
            'order': 5
        },
        {
            'category': 'Ventas',
            'name': 'Comisiones',
            'url': '/sales/commissions/',
            'icon': 'fas fa-percentage',
            'order': 6
        },
        
        # CRM y Comunicaciones
        {
            'category': 'CRM',
            'name': 'Dashboard CRM',
            'url': '/crm/dashboard/',
            'icon': 'fas fa-handshake',
            'order': 1
        },
        {
            'category': 'CRM',
            'name': 'Contactos',
            'url': '/crm/contacts/',
            'icon': 'fas fa-address-book',
            'order': 2
        },
        {
            'category': 'CRM',
            'name': 'Actividades',
            'url': '/crm/activities/',
            'icon': 'fas fa-calendar-check',
            'order': 3
        },
        {
            'category': 'CRM',
            'name': 'WhatsApp Business',
            'url': '/whatsapp/',
            'icon': 'fab fa-whatsapp',
            'order': 4
        },
        {
            'category': 'CRM',
            'name': 'Email Marketing',
            'url': '/crm/email/',
            'icon': 'fas fa-envelope',
            'order': 5
        },
        {
            'category': 'CRM',
            'name': 'Seguimientos',
            'url': '/crm/followups/',
            'icon': 'fas fa-eye',
            'order': 6
        },
        
        # Reportes y Analytics
        {
            'category': 'Reportes',
            'name': 'Dashboard de Reportes',
            'url': '/reports/dashboard/',
            'icon': 'fas fa-chart-bar',
            'order': 1
        },
        {
            'category': 'Reportes',
            'name': 'Reportes de Ventas',
            'url': '/reports/sales/',
            'icon': 'fas fa-chart-pie',
            'order': 2
        },
        {
            'category': 'Reportes',
            'name': 'Reportes de Proyectos',
            'url': '/reports/projects/',
            'icon': 'fas fa-building',
            'order': 3
        },
        {
            'category': 'Reportes',
            'name': 'Analytics de CRM',
            'url': '/reports/crm/',
            'icon': 'fas fa-analytics',
            'order': 4
        },
        {
            'category': 'Reportes',
            'name': 'Estadísticas Generales',
            'url': '/reports/stats/',
            'icon': 'fas fa-calculator',
            'order': 5
        },
        {
            'category': 'Reportes',
            'name': 'Exportar Datos',
            'url': '/reports/export/',
            'icon': 'fas fa-download',
            'order': 6
        },
        
        # Configuración del Sistema
        {
            'category': 'Configuración',
            'name': 'Configuración General',
            'url': '/config/',
            'icon': 'fas fa-sliders-h',
            'order': 1
        },
        {
            'category': 'Configuración',
            'name': 'Parámetros del Sistema',
            'url': '/config/params/',
            'icon': 'fas fa-cogs',
            'order': 2
        },
        {
            'category': 'Configuración',
            'name': 'Categorías de Menú',
            'url': '/config/categories/',
            'icon': 'fas fa-folder-open',
            'order': 3
        },
        {
            'category': 'Configuración',
            'name': 'Navegación del Sistema',
            'url': '/config/navigation/',
            'icon': 'fas fa-sitemap',
            'order': 4
        },
        {
            'category': 'Configuración',
            'name': 'Plantillas de Email',
            'url': '/config/email-templates/',
            'icon': 'fas fa-envelope-open-text',
            'order': 5
        },
        {
            'category': 'Configuración',
            'name': 'Integraciones',
            'url': '/config/integrations/',
            'icon': 'fas fa-plug',
            'order': 6
        }
    ]
    
    created_groups = {}
    for nav_data in navigation_data:
        # Crear grupo
        group, group_created = Group.objects.get_or_create(
            name=nav_data['name']
        )
        created_groups[nav_data['name']] = group
        
        # Crear navegación
        category = categories[nav_data['category']]
        navigation, nav_created = Navigation.objects.get_or_create(
            group=group,
            defaults={
                'name': nav_data['name'],
                'url': nav_data['url'],
                'icon': nav_data['icon'],
                'order': nav_data['order'],
                'category': category,
                'is_active': True
            }
        )
        
        status = "✅ Creado" if group_created else "ℹ️  Ya existe"
        print(f"  {status}: {nav_data['category']} - {nav_data['name']}")
    
    return created_groups

def create_super_admin_role(groups):
    """Crear solo el rol Super Admin con acceso a todos los módulos"""
    print("👥 Creando rol Super Admin...")
    
    # Crear o obtener rol de Super Admin
    super_admin_role, created = Role.objects.get_or_create(
        name='Super Admin',
        defaults={
            'description': 'Administrador con acceso completo a todos los módulos del sistema',
            'is_system': True,
            'is_active': True
        }
    )
    
    # Limpiar grupos existentes y asignar todos los módulos
    super_admin_role.groups.clear()
    for group_name, group in groups.items():
        super_admin_role.groups.add(group)
    
    status = "✅ Creado" if created else "ℹ️  Ya existe (actualizado)"
    print(f"  {status}: {super_admin_role.name}")
    print(f"  📦 Módulos asignados: {super_admin_role.groups.count()}")
    
    return {'Super Admin': super_admin_role}

def assign_admin_user_role(roles):
    """Asignar rol Super Admin al usuario admin"""
    print("🔑 Asignando roles a usuarios...")
    
    try:
        admin_user = User.objects.get(username='admin')
        super_admin_role = roles.get('Super Admin')
        
        if super_admin_role:
            admin_user.role = super_admin_role
            admin_user.save()
            print(f"  ✅ Usuario '{admin_user.username}' asignado al rol: {super_admin_role.name}")
        else:
            print("  ⚠️  Rol Super Admin no encontrado")
            
    except User.DoesNotExist:
        print("  ⚠️  Usuario admin no encontrado. Ejecuta primero el script de reset de base de datos.")

def create_default_permissions():
    """Crear permisos personalizados del sistema"""
    print("🔒 Creando permisos personalizados...")
    
    # Obtener content types relevantes
    try:
        user_ct = ContentType.objects.get_for_model(User)
        role_ct = ContentType.objects.get_for_model(Role)
        
        custom_permissions = [
            # Permisos de usuarios
            {
                'codename': 'can_manage_users',
                'name': 'Puede gestionar usuarios',
                'content_type': user_ct
            },
            {
                'codename': 'can_reset_passwords',
                'name': 'Puede resetear contraseñas',
                'content_type': user_ct
            },
            {
                'codename': 'can_export_users',
                'name': 'Puede exportar datos de usuarios',
                'content_type': user_ct
            },
            
            # Permisos de roles
            {
                'codename': 'can_manage_roles',
                'name': 'Puede gestionar roles',
                'content_type': role_ct
            },
            {
                'codename': 'can_assign_roles',
                'name': 'Puede asignar roles a usuarios',
                'content_type': role_ct
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

def main():
    """Función principal del script"""
    print("🚀 Configurando roles, navegación y permisos del sistema...")
    print("=" * 60)
    
    # 1. Crear categorías del menú
    categories = create_categories()
    print()
    
    # 2. Crear módulos de navegación
    groups = create_navigation_modules(categories)
    print()
    
    # 3. Crear permisos personalizados
    permissions = create_default_permissions()
    print()
    
    # 4. Crear rol Super Admin y asignar todos los módulos
    roles = create_super_admin_role(groups)
    print()
    
    # 5. Asignar rol al usuario admin
    assign_admin_user_role(roles)
    print()
    
    # Resumen final
    print("=" * 60)
    print("🎉 Configuración completada exitosamente:")
    print(f"   📁 Categorías creadas: {len(categories)}")
    print(f"   🧭 Módulos del sidebar: {len(groups)}")
    print(f"   👥 Rol Super Admin configurado: 1")
    print(f"   🔒 Permisos personalizados: {len(permissions)}")
    print()
    
    # Mostrar detalles del rol Super Admin
    super_admin = roles.get('Super Admin')
    if super_admin:
        print("📋 Detalle del rol Super Admin:")
        print(f"   • Acceso completo a {super_admin.groups.count()} módulos")
        print("   • Roles adicionales pueden crearse según necesidad")
    print()
    
    print("✨ Sistema base configurado y listo para usar!")
    print("💡 Nota: Otros roles pueden crearse posteriormente según las necesidades específicas.")

if __name__ == "__main__":
    main()