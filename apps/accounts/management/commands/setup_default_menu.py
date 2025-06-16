# Crear archivo: apps/accounts/management/commands/setup_default_menu.py

import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import MenuCategory, Navigation


class Command(BaseCommand):
    help = 'Crea la estructura de menú por defecto para el sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la recreación de categorías existentes',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Configurando estructura de menú por defecto...'))

        # 1. Crear categorías por defecto
        self.create_default_categories(options['force'])

        # 2. Asignar módulos existentes a categorías
        self.assign_existing_modules()

        # 3. Crear módulos básicos si no existen
        self.create_basic_modules()

        self.stdout.write(
            self.style.SUCCESS('✅ Estructura de menú configurada exitosamente!')
        )

    def create_default_categories(self, force=False):
        """Crea las categorías por defecto del sistema"""

        default_categories = [
            {
                'name': 'DASHBOARDS',
                'description': 'Panel principal de usuario',
                'icon': 'fas fa-tachometer-alt',
                'color': 'blue',
                'order': 10,
                'is_system': True
            },
            {
                'name': 'ADMINISTRACIÓN DEL SISTEMA',
                'description': 'Gestión de módulos, roles y usuarios',
                'icon': 'fas fa-cogs',
                'color': 'red',
                'order': 20,
                'is_system': True
            },
            {
                'name': 'VENTAS',
                'description': 'Gestión de ventas y clientes',
                'icon': 'fas fa-chart-line',
                'color': 'green',
                'order': 30,
                'is_system': False
            },
            {
                'name': 'RECURSOS HUMANOS',
                'description': 'Gestión de empleados y nóminas',
                'icon': 'fas fa-users',
                'color': 'purple',
                'order': 40,
                'is_system': False
            },
            {
                'name': 'REPORTES',
                'description': 'Análisis y reportes del sistema',
                'icon': 'fas fa-chart-bar',
                'color': 'yellow',
                'order': 50,
                'is_system': False
            }
        ]

        for cat_data in default_categories:
            category, created = MenuCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )

            if created:
                self.stdout.write(f"  ✅ Categoría creada: {category.name}")
            elif force:
                for key, value in cat_data.items():
                    setattr(category, key, value)
                category.save()
                self.stdout.write(f"  🔄 Categoría actualizada: {category.name}")
            else:
                self.stdout.write(f"  ⏭️  Categoría ya existe: {category.name}")

    def assign_existing_modules(self):
        """Asigna módulos existentes a categorías apropiadas"""

        # Obtener categorías
        try:
            admin_category = MenuCategory.objects.get(name='ADMINISTRACIÓN DEL SISTEMA')
            ventas_category = MenuCategory.objects.get(name='VENTAS')
        except MenuCategory.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('❌ No se encontraron las categorías necesarias')
            )
            return

        # Asignar módulos existentes por nombre
        module_assignments = {
            # Módulos de administración
            admin_category: [
                'Administradores del Sistema',
                'Gestión de Usuarios',
                'Configuración',
                'Sistema'
            ],
            # Módulos de ventas
            ventas_category: [
                'Ventas',
                'Clientes',
                'Productos',
                'Gestión de Clientes',
                'Gestión de Ventas'
            ]
        }

        for category, module_names in module_assignments.items():
            for module_name in module_names:
                try:
                    # Buscar grupos que contengan el nombre (parcial)
                    groups = Group.objects.filter(name__icontains=module_name)

                    for group in groups:
                        if hasattr(group, 'navigation') and group.navigation:
                            if not group.navigation.category:
                                group.navigation.category = category
                                group.navigation.save()
                                self.stdout.write(
                                    f"  📌 {group.name} → {category.name}"
                                )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠️  Error asignando {module_name}: {e}")
                    )

    def create_basic_modules(self):
        """Crea módulos básicos si no existen"""

        # Obtener categoría de ventas
        try:
            ventas_category = MenuCategory.objects.get(name='VENTAS')
            rrhh_category = MenuCategory.objects.get(name='RECURSOS HUMANOS')
            reportes_category = MenuCategory.objects.get(name='REPORTES')
        except MenuCategory.DoesNotExist:
            return

        # Módulos básicos a crear
        basic_modules = [
            {
                'group_name': 'Gestión de Clientes',
                'navigation': {
                    'name': 'Clientes',
                    'url': '/customers/',
                    'icon': 'fas fa-users',
                    'order': 10,
                    'category': ventas_category
                },
                'permissions': ['auth.view_user']  # Permisos básicos
            },
            {
                'group_name': 'Gestión de Productos',
                'navigation': {
                    'name': 'Productos',
                    'url': '/products/',
                    'icon': 'fas fa-boxes',
                    'order': 20,
                    'category': ventas_category
                },
                'permissions': []
            },
            {
                'group_name': 'Empleados',
                'navigation': {
                    'name': 'Empleados',
                    'url': '/employees/',
                    'icon': 'fas fa-id-badge',
                    'order': 10,
                    'category': rrhh_category
                },
                'permissions': []
            },
            {
                'group_name': 'Reportes de Ventas',
                'navigation': {
                    'name': 'Reportes',
                    'url': '/reports/',
                    'icon': 'fas fa-chart-pie',
                    'order': 10,
                    'category': reportes_category
                },
                'permissions': []
            }
        ]

        for module_data in basic_modules:
            # Crear grupo si no existe
            group, group_created = Group.objects.get_or_create(
                name=module_data['group_name']
            )

            if group_created:
                self.stdout.write(f"  ✅ Módulo creado: {group.name}")

                # Asignar permisos
                if module_data['permissions']:
                    permissions = Permission.objects.filter(
                        codename__in=module_data['permissions']
                    )
                    group.permissions.set(permissions)

                # Crear navegación
                Navigation.objects.get_or_create(
                    group=group,
                    defaults=module_data['navigation']
                )
            else:
                self.stdout.write(f"  ⏭️  Módulo ya existe: {group.name}")


# ============================================================
# APPS CONFIG - Auto-ejecutar al iniciar
# ============================================================

# En apps/accounts/apps.py - ACTUALIZAR:

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Accounts'

    def ready(self):
        """Se ejecuta cuando la app está lista"""
        # Solo ejecutar en el proceso principal (no en migraciones)
        import os
        import django
        from django.db import connection

        if os.environ.get('RUN_MAIN'):  # Solo en desarrollo con runserver
            try:
                # Verificar que las tablas existan
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_menucategory';"
                    )
                    if cursor.fetchone():
                        # Ejecutar setup automático
                        from django.core.management import call_command
                        call_command('setup_default_menu', verbosity=0)
            except Exception:
                # Si hay error (ej: tablas no existen), ignorar
                pass