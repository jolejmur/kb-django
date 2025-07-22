#!/usr/bin/env python
"""
Script para crear módulos de Marketing Digital en el sidebar
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
    print("📱 Configurando módulos de Marketing Digital...")
    
    # Crear categoría para Marketing Digital
    category, created = MenuCategory.objects.get_or_create(
        name='Marketing Digital',
        defaults={
            'description': 'Gestión de campañas, leads y WhatsApp Business',
            'icon': 'fas fa-megaphone',
            'color': 'info',
            'order': 3,
            'is_active': True
        }
    )
    
    if created:
        print(f"✅ Categoría creada: {category.name}")
    else:
        print(f"ℹ️  Categoría ya existe: {category.name}")
    
    # Crear grupos/módulos para Marketing Digital
    modules = [
        {
            'name': 'Dashboard Marketing',
            'url': '/marketing/',
            'icon': 'fas fa-chart-pie',
            'order': 1
        },
        {
            'name': 'Configuración Meta Business',
            'url': '/marketing/configuracion/',
            'icon': 'fab fa-meta',
            'order': 2
        },
        {
            'name': 'Gestión de Templates',
            'url': '/marketing/templates/',
            'icon': 'fas fa-file-alt',
            'order': 3
        },
        {
            'name': 'Campañas Facebook',
            'url': '/marketing/campañas-facebook/',
            'icon': 'fab fa-facebook',
            'order': 4
        },
        {
            'name': 'Gestión de Leads',
            'url': '/marketing/leads/',
            'icon': 'fas fa-user-plus',
            'order': 5
        },
        {
            'name': 'Asignación de Leads',
            'url': '/marketing/asignacion-leads/',
            'icon': 'fas fa-user-check',
            'order': 6
        },
        {
            'name': 'Chat',
            'url': '/marketing/chat/',
            'icon': 'fas fa-comments',
            'order': 7
        },
        {
            'name': 'Supervisión de Chat',
            'url': '/marketing/supervision-chat/',
            'icon': 'fas fa-eye',
            'order': 8
        },
        {
            'name': 'Reportes Marketing',
            'url': '/marketing/reportes/',
            'icon': 'fas fa-chart-line',
            'order': 9
        },
        {
            'name': 'Integraciones',
            'url': '/marketing/integraciones/',
            'icon': 'fas fa-plug',
            'order': 10
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
    
    # Asignar todos los grupos de Marketing Digital al rol
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
    
    # Crear roles específicos para Marketing Digital
    marketing_roles = [
        {
            'name': 'Marketing Manager',
            'description': 'Gestor de marketing con acceso completo a campañas y leads',
            'groups': [
                'Dashboard Marketing',
                'Configuración Meta Business',
                'Gestión de Templates',
                'Campañas Facebook',
                'Gestión de Leads',
                'Asignación de Leads',
                'Chat',
                'Supervisión de Chat',
                'Reportes Marketing',
                'Integraciones'
            ]
        },
        {
            'name': 'Marketing Specialist',
            'description': 'Especialista en marketing con acceso limitado',
            'groups': [
                'Dashboard Marketing',
                'Gestión de Templates',
                'Campañas Facebook',
                'Gestión de Leads',
                'Chat',
                'Reportes Marketing'
            ]
        },
        {
            'name': 'Content Creator',
            'description': 'Creador de contenido con acceso a templates',
            'groups': [
                'Dashboard Marketing',
                'Gestión de Templates',
                'Campañas Facebook'
            ]
        }
    ]
    
    print("\n🎯 Creando roles específicos de Marketing Digital...")
    for role_data in marketing_roles:
        role, role_created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={
                'description': role_data['description'],
                'is_active': True,
                'is_system': False
            }
        )
        
        # Asignar grupos al rol
        for group_name in role_data['groups']:
            try:
                group = Group.objects.get(name=group_name)
                role.groups.add(group)
            except Group.DoesNotExist:
                print(f"⚠️  Grupo no encontrado: {group_name}")
        
        status = "✅ Creado" if role_created else "ℹ️  Ya existe"
        print(f"{status}: {role_data['name']} - {role.groups.count()} módulos")
    
    # Crear permisos específicos para jerarquía de equipos en Marketing
    print("\n👥 Configurando permisos para jerarquía de equipos...")
    
    # Grupos específicos para Team Leaders en Marketing
    team_leader_marketing_groups = [
        'Dashboard Marketing',
        'Gestión de Leads',
        'Asignación de Leads',
        'Chat',
        'Supervisión de Chat',
        'Reportes Marketing'
    ]
    
    # Grupos específicos para Vendedores en Marketing
    vendedor_marketing_groups = [
        'Chat',
        'Reportes Marketing'
    ]
    
    # Crear roles para la jerarquía de equipos en Marketing
    jerarquia_roles = [
        {
            'name': 'Team Leader Marketing',
            'description': 'Team Leader con acceso a asignación de leads y supervisión de chat',
            'groups': team_leader_marketing_groups
        },
        {
            'name': 'Vendedor Marketing',
            'description': 'Vendedor con acceso a chat y reportes básicos',
            'groups': vendedor_marketing_groups
        }
    ]
    
    for role_data in jerarquia_roles:
        role, role_created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={
                'description': role_data['description'],
                'is_active': True,
                'is_system': False
            }
        )
        
        # Asignar grupos al rol
        for group_name in role_data['groups']:
            try:
                group = Group.objects.get(name=group_name)
                role.groups.add(group)
            except Group.DoesNotExist:
                print(f"⚠️  Grupo no encontrado: {group_name}")
        
        status = "✅ Creado" if role_created else "ℹ️  Ya existe"
        print(f"{status}: {role_data['name']} - {role.groups.count()} módulos")
    
    print(f"\n🎉 Configuración completada:")
    print(f"   - Categoría: {category.name}")
    print(f"   - Módulos creados: {len(created_groups)}")
    print(f"   - Rol Super Admin: {super_admin_role.name}")
    print(f"   - Total grupos asignados al Super Admin: {super_admin_role.groups.count()}")
    print(f"   - Roles específicos creados: {len(marketing_roles) + len(jerarquia_roles)}")
    
    print(f"\n📋 Módulos creados:")
    for module in modules:
        print(f"   • {module['name']} ({module['url']})")
    
    print(f"\n🔐 Roles específicos:")
    for role in marketing_roles + jerarquia_roles:
        print(f"   • {role['name']}")
    
    print(f"\n🎯 Módulos específicos para Team Leaders:")
    print(f"   • Asignación de Leads: donde los team leaders asignan leads a sus vendedores")
    print(f"   • Supervisión de Chat: donde pueden ver los chats de todos sus subalternos")
    
    print(f"\n✨ Cambios implementados:")
    print(f"   • Campañas WhatsApp → Campañas Facebook")
    print(f"   • Conversaciones → Chat")
    print(f"   • Agregado: Asignación de Leads")
    print(f"   • Agregado: Supervisión de Chat")

if __name__ == "__main__":
    main()