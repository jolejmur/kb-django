# apps/sales/management/commands/setup_sales_modules.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import MenuCategory, Navigation, Role
from apps.sales_team_management.models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    ComisionDesarrollo, ComisionVenta
)


class Command(BaseCommand):
    help = 'Configura los módulos y permisos para el sistema de ventas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Limpia módulos existentes antes de crear',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🏗️ Configurando módulos de ventas...'))

        if options['clean']:
            self.clean_sales_modules()

        # 1. Crear categoría de VENTAS
        sales_category = self.create_sales_category()

        # 2. Crear módulos de ventas
        self.create_sales_modules(sales_category)

        # 3. Asignar módulos al superadmin
        self.assign_to_superadmin()

        self.stdout.write(
            self.style.SUCCESS('✅ Módulos de ventas configurados exitosamente!')
        )

    def clean_sales_modules(self):
        """Limpia módulos de ventas existentes"""
        self.stdout.write("🧹 Limpiando módulos de ventas existentes...")

        sales_modules = [
            'Gestión de Equipos de Venta',
            'Gestión de Proyectos',
            'Gestión de Inmuebles',
            'Configuración de Comisiones',
            'Roles de Ventas',
            'Dashboard de Ventas'
        ]

        Group.objects.filter(name__in=sales_modules).delete()
        self.stdout.write("  🗑️ Módulos de ventas eliminados")

    def create_sales_category(self):
        """Crea la categoría de VENTAS"""
        category_data = {
            'name': 'VENTAS',
            'description': 'Gestión de equipos de venta, proyectos inmobiliarios y comisiones',
            'icon': 'fas fa-chart-line',
            'color': 'green',
            'order': 30,
            'is_system': False,
            'is_active': True
        }

        category, created = MenuCategory.objects.get_or_create(
            name=category_data['name'],
            defaults=category_data
        )

        if created:
            self.stdout.write(f"  ✅ Categoría creada: {category.name}")
        else:
            self.stdout.write(f"  ⏭️ Categoría ya existe: {category.name}")

        return category

    def create_sales_modules(self, sales_category):
        """Crea los módulos del sistema de ventas"""

        # Obtener content types
        equipoventa_ct = ContentType.objects.get_for_model(EquipoVenta)
        gerenteequipo_ct = ContentType.objects.get_for_model(GerenteEquipo)
        jefeVenta_ct = ContentType.objects.get_for_model(JefeVenta)
        teamleader_ct = ContentType.objects.get_for_model(TeamLeader)
        vendedor_ct = ContentType.objects.get_for_model(Vendedor)
        gerenteproyecto_ct = ContentType.objects.get_for_model(GerenteProyecto)
        jefeproyecto_ct = ContentType.objects.get_for_model(JefeProyecto)
        proyecto_ct = ContentType.objects.get_for_model(Proyecto)
        inmueble_ct = ContentType.objects.get_for_model(Inmueble)
        comisiondesarrollo_ct = ContentType.objects.get_for_model(ComisionDesarrollo)
        comisionventa_ct = ContentType.objects.get_for_model(ComisionVenta)

        sales_modules_config = [
            # 1. GESTIÓN DE EQUIPOS DE VENTA
            {
                'group_name': 'Gestión de Equipos de Venta',
                'navigation': {
                    'name': 'Equipos de Venta',
                    'url': '/sales/equipos/',
                    'icon': 'fas fa-users',
                    'order': 10,
                    'category': sales_category
                },
                'permissions': [
                    f'{equipoventa_ct.app_label}.add_equipoventa',
                    f'{equipoventa_ct.app_label}.change_equipoventa',
                    f'{equipoventa_ct.app_label}.delete_equipoventa',
                    f'{equipoventa_ct.app_label}.view_equipoventa',
                    f'{gerenteequipo_ct.app_label}.add_gerenteequipo',
                    f'{gerenteequipo_ct.app_label}.change_gerenteequipo',
                    f'{gerenteequipo_ct.app_label}.delete_gerenteequipo',
                    f'{gerenteequipo_ct.app_label}.view_gerenteequipo',
                    f'{jefeVenta_ct.app_label}.view_jefeventa',
                    f'{teamleader_ct.app_label}.view_teamleader',
                    f'{vendedor_ct.app_label}.view_vendedor',
                ]
            },

            # 2. GESTIÓN DE PROYECTOS
            {
                'group_name': 'Gestión de Proyectos',
                'navigation': {
                    'name': 'Proyectos',
                    'url': '/sales/proyectos/',
                    'icon': 'fas fa-building',
                    'order': 20,
                    'category': sales_category
                },
                'permissions': [
                    f'{proyecto_ct.app_label}.add_proyecto',
                    f'{proyecto_ct.app_label}.change_proyecto',
                    f'{proyecto_ct.app_label}.delete_proyecto',
                    f'{proyecto_ct.app_label}.view_proyecto',
                    f'{gerenteproyecto_ct.app_label}.view_gerenteproyecto',
                    f'{jefeproyecto_ct.app_label}.view_jefeproyecto',
                ]
            },

            # 3. GESTIÓN DE INMUEBLES
            {
                'group_name': 'Gestión de Inmuebles',
                'navigation': {
                    'name': 'Inmuebles',
                    'url': '/sales/proyectos/',  # Redirige a proyectos donde se pueden ver inmuebles
                    'icon': 'fas fa-home',
                    'order': 30,
                    'category': sales_category
                },
                'permissions': [
                    f'{inmueble_ct.app_label}.add_inmueble',
                    f'{inmueble_ct.app_label}.change_inmueble',
                    f'{inmueble_ct.app_label}.delete_inmueble',
                    f'{inmueble_ct.app_label}.view_inmueble',
                    f'{proyecto_ct.app_label}.view_proyecto',
                ]
            },

            # 4. CONFIGURACIÓN DE COMISIONES
            {
                'group_name': 'Configuración de Comisiones',
                'navigation': {
                    'name': 'Comisiones',
                    'url': '/sales/equipos/',  # Desde equipos y proyectos se accede a comisiones
                    'icon': 'fas fa-percentage',
                    'order': 40,
                    'category': sales_category
                },
                'permissions': [
                    f'{comisionventa_ct.app_label}.add_comisionventa',
                    f'{comisionventa_ct.app_label}.change_comisionventa',
                    f'{comisionventa_ct.app_label}.delete_comisionventa',
                    f'{comisionventa_ct.app_label}.view_comisionventa',
                    f'{comisiondesarrollo_ct.app_label}.add_comisiondesarrollo',
                    f'{comisiondesarrollo_ct.app_label}.change_comisiondesarrollo',
                    f'{comisiondesarrollo_ct.app_label}.delete_comisiondesarrollo',
                    f'{comisiondesarrollo_ct.app_label}.view_comisiondesarrollo',
                ]
            },

            # 5. ROLES DE VENTAS
            {
                'group_name': 'Roles de Ventas',
                'navigation': {
                    'name': 'Roles de Ventas',
                    'url': '/sales/equipos/',  # Gestión desde equipos
                    'icon': 'fas fa-user-tie',
                    'order': 50,
                    'category': sales_category
                },
                'permissions': [
                    f'{jefeVenta_ct.app_label}.add_jefeventa',
                    f'{jefeVenta_ct.app_label}.change_jefeventa',
                    f'{jefeVenta_ct.app_label}.delete_jefeventa',
                    f'{jefeVenta_ct.app_label}.view_jefeventa',
                    f'{teamleader_ct.app_label}.add_teamleader',
                    f'{teamleader_ct.app_label}.change_teamleader',
                    f'{teamleader_ct.app_label}.delete_teamleader',
                    f'{teamleader_ct.app_label}.view_teamleader',
                    f'{vendedor_ct.app_label}.add_vendedor',
                    f'{vendedor_ct.app_label}.change_vendedor',
                    f'{vendedor_ct.app_label}.delete_vendedor',
                    f'{vendedor_ct.app_label}.view_vendedor',
                    f'{gerenteproyecto_ct.app_label}.add_gerenteproyecto',
                    f'{gerenteproyecto_ct.app_label}.change_gerenteproyecto',
                    f'{gerenteproyecto_ct.app_label}.delete_gerenteproyecto',
                    f'{gerenteproyecto_ct.app_label}.view_gerenteproyecto',
                    f'{jefeproyecto_ct.app_label}.add_jefeproyecto',
                    f'{jefeproyecto_ct.app_label}.change_jefeproyecto',
                    f'{jefeproyecto_ct.app_label}.delete_jefeproyecto',
                    f'{jefeproyecto_ct.app_label}.view_jefeproyecto',
                ]
            },

            # 6. DASHBOARD DE VENTAS
            {
                'group_name': 'Dashboard de Ventas',
                'navigation': {
                    'name': 'Dashboard de Ventas',
                    'url': '/sales/',
                    'icon': 'fas fa-tachometer-alt',
                    'order': 60,
                    'category': sales_category
                },
                'permissions': [
                    f'{proyecto_ct.app_label}.view_proyecto',
                    f'{equipoventa_ct.app_label}.view_equipoventa',
                    f'{inmueble_ct.app_label}.view_inmueble',
                ]
            }
        ]

        created_groups = []

        for module_data in sales_modules_config:
            # Crear grupo
            group, group_created = Group.objects.get_or_create(
                name=module_data['group_name']
            )

            if group_created:
                self.stdout.write(f"  ✅ Módulo creado: {group.name}")
            else:
                self.stdout.write(f"  ⏭️ Módulo ya existe: {group.name}")

            created_groups.append(group)

            # Limpiar y asignar permisos
            group.permissions.clear()
            permissions_to_assign = []

            for perm_codename in module_data['permissions']:
                try:
                    app_label, codename = perm_codename.split('.')
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    permissions_to_assign.append(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"    ⚠️ Permiso no encontrado: {perm_codename}")
                    )

            if permissions_to_assign:
                group.permissions.set(permissions_to_assign)
                self.stdout.write(f"    📋 Asignados {len(permissions_to_assign)} permisos")

            # Crear navegación
            navigation_data = module_data['navigation'].copy()
            navigation, nav_created = Navigation.objects.get_or_create(
                group=group,
                defaults=navigation_data
            )

            if nav_created:
                self.stdout.write(f"    🔗 Navegación creada: {navigation.name}")
            else:
                # Actualizar navegación existente
                for key, value in navigation_data.items():
                    setattr(navigation, key, value)
                navigation.save()
                self.stdout.write(f"    🔄 Navegación actualizada: {navigation.name}")

        return created_groups

    def assign_to_superadmin(self):
        """Asigna los módulos de ventas al rol de superadmin"""
        try:
            superadmin_role = Role.objects.get(name='Super Administrador')

            # Obtener módulos de ventas
            sales_modules = Group.objects.filter(
                name__in=[
                    'Gestión de Equipos de Venta',
                    'Gestión de Proyectos',
                    'Gestión de Inmuebles',
                    'Configuración de Comisiones',
                    'Roles de Ventas',
                    'Dashboard de Ventas'
                ]
            )

            # Agregar módulos al rol existente (no reemplazar)
            current_groups = list(superadmin_role.groups.all())
            new_groups = current_groups + list(sales_modules)
            superadmin_role.groups.set(new_groups)

            self.stdout.write(
                f"  📦 {sales_modules.count()} módulos de ventas asignados al superadmin"
            )

        except Role.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('  ⚠️ Rol "Super Administrador" no encontrado')
            )