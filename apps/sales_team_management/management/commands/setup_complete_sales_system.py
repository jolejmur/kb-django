# apps/sales/management/commands/setup_complete_sales_system.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import MenuCategory, Navigation, Role
from apps.sales_team_management.models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    ComisionDesarrollo, ComisionVenta, AsignacionEquipoProyecto
)


class Command(BaseCommand):
    help = 'Configura el sistema completo de ventas con categorías y módulos separados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Limpia módulos existentes antes de crear',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🏗️ Configurando sistema completo de ventas...'))

        if options['clean']:
            self.clean_sales_system()

        # 1. Crear categorías separadas
        development_category = self.create_development_category()
        sales_category = self.create_sales_category()
        leads_category = self.create_leads_category()
        commissions_category = self.create_commissions_category()

        # 2. Crear módulos por categoría
        self.create_development_modules(development_category)
        self.create_sales_modules(sales_category)
        self.create_leads_modules(leads_category)
        self.create_commissions_modules(commissions_category)

        # 3. Asignar todos los módulos al superadmin
        self.assign_to_superadmin()

        self.stdout.write(
            self.style.SUCCESS('✅ Sistema completo de ventas configurado exitosamente!')
        )

    def clean_sales_system(self):
        """Limpia módulos y categorías existentes"""
        self.stdout.write("🧹 Limpiando sistema de ventas existente...")

        # Eliminar categorías
        categories_to_delete = ['DESARROLLO', 'VENTAS', 'LEADS & CRM', 'COMISIONES']
        MenuCategory.objects.filter(name__in=categories_to_delete).delete()

        # Eliminar grupos/módulos
        modules_to_delete = [
            # Desarrollo
            'Gestión de Proyectos',
            'Gestión de Inmuebles', 
            'Roles de Desarrollo',
            'Dashboard de Proyectos',
            
            # Ventas
            'Gestión de Equipos de Venta',
            'Jerarquía de Ventas',
            'Asignación Proyecto-Equipo',
            'Dashboard de Ventas',
            
            # Leads & CRM
            'Gestión de Campañas',
            'Gestión de Leads',
            'Proceso de Venta',
            'Cotizaciones',
            'Dashboard CRM',
            
            # Comisiones
            'Comisiones de Desarrollo',
            'Comisiones de Venta',
            'Comisiones Generadas',
            'Reportes de Comisiones'
        ]
        Group.objects.filter(name__in=modules_to_delete).delete()
        self.stdout.write("  🗑️ Sistema anterior eliminado")

    def create_development_category(self):
        """Crea la categoría de DESARROLLO"""
        category_data = {
            'name': 'DESARROLLO',
            'description': 'Gestión de proyectos inmobiliarios, inmuebles y roles de desarrollo',
            'icon': 'fas fa-building',
            'color': 'blue',
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

    def create_sales_category(self):
        """Crea la categoría de VENTAS"""
        category_data = {
            'name': 'VENTAS',
            'description': 'Gestión de equipos de venta, jerarquías y asignaciones',
            'icon': 'fas fa-users',
            'color': 'green',
            'order': 31,
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

    def create_leads_category(self):
        """Crea la categoría de LEADS & CRM"""
        category_data = {
            'name': 'LEADS & CRM',
            'description': 'Gestión de campañas, leads, procesos de venta y cotizaciones',
            'icon': 'fas fa-chart-line',
            'color': 'purple',
            'order': 32,
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

    def create_commissions_category(self):
        """Crea la categoría de COMISIONES"""
        category_data = {
            'name': 'COMISIONES',
            'description': 'Gestión de comisiones de desarrollo, venta y reportes',
            'icon': 'fas fa-percentage',
            'color': 'yellow',
            'order': 33,
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

    def create_development_modules(self, category):
        """Crea los módulos de DESARROLLO"""
        self.stdout.write("\n📦 Creando módulos de DESARROLLO...")

        # Obtener content types
        proyecto_ct = ContentType.objects.get_for_model(Proyecto)
        inmueble_ct = ContentType.objects.get_for_model(Inmueble)
        gerenteproyecto_ct = ContentType.objects.get_for_model(GerenteProyecto)
        jefeproyecto_ct = ContentType.objects.get_for_model(JefeProyecto)

        modules_config = [
            # 1. GESTIÓN DE PROYECTOS
            {
                'group_name': 'Gestión de Proyectos',
                'navigation': {
                    'name': 'Proyectos',
                    'url': '/sales/proyectos/',
                    'icon': 'fas fa-building',
                    'order': 10,
                    'category': category
                },
                'permissions': [
                    f'{proyecto_ct.app_label}.add_proyecto',
                    f'{proyecto_ct.app_label}.change_proyecto',
                    f'{proyecto_ct.app_label}.delete_proyecto',
                    f'{proyecto_ct.app_label}.view_proyecto',
                ]
            },

            # 2. GESTIÓN DE INMUEBLES
            {
                'group_name': 'Gestión de Inmuebles',
                'navigation': {
                    'name': 'Inmuebles',
                    'url': '/sales/proyectos/',
                    'icon': 'fas fa-home',
                    'order': 20,
                    'category': category
                },
                'permissions': [
                    f'{inmueble_ct.app_label}.add_inmueble',
                    f'{inmueble_ct.app_label}.change_inmueble',
                    f'{inmueble_ct.app_label}.delete_inmueble',
                    f'{inmueble_ct.app_label}.view_inmueble',
                    f'{proyecto_ct.app_label}.view_proyecto',
                ]
            },

            # 3. ROLES DE DESARROLLO
            {
                'group_name': 'Roles de Desarrollo',
                'navigation': {
                    'name': 'Roles de Desarrollo',
                    'url': '/sales/proyectos/',
                    'icon': 'fas fa-user-cog',
                    'order': 30,
                    'category': category
                },
                'permissions': [
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

            # 4. DASHBOARD DE PROYECTOS
            {
                'group_name': 'Dashboard de Proyectos',
                'navigation': {
                    'name': 'Dashboard Proyectos',
                    'url': '/sales/',
                    'icon': 'fas fa-chart-bar',
                    'order': 40,
                    'category': category
                },
                'permissions': [
                    f'{proyecto_ct.app_label}.view_proyecto',
                    f'{inmueble_ct.app_label}.view_inmueble',
                ]
            }
        ]

        return self.create_modules(modules_config)

    def create_sales_modules(self, category):
        """Crea los módulos de VENTAS"""
        self.stdout.write("\n📦 Creando módulos de VENTAS...")

        # Obtener content types
        equipoventa_ct = ContentType.objects.get_for_model(EquipoVenta)
        gerenteequipo_ct = ContentType.objects.get_for_model(GerenteEquipo)
        jefeventa_ct = ContentType.objects.get_for_model(JefeVenta)
        teamleader_ct = ContentType.objects.get_for_model(TeamLeader)
        vendedor_ct = ContentType.objects.get_for_model(Vendedor)
        asignacion_ct = ContentType.objects.get_for_model(AsignacionEquipoProyecto)

        modules_config = [
            # 1. GESTIÓN DE EQUIPOS DE VENTA
            {
                'group_name': 'Gestión de Equipos de Venta',
                'navigation': {
                    'name': 'Equipos de Venta',
                    'url': '/sales/equipos/',
                    'icon': 'fas fa-users',
                    'order': 10,
                    'category': category
                },
                'permissions': [
                    f'{equipoventa_ct.app_label}.add_equipoventa',
                    f'{equipoventa_ct.app_label}.change_equipoventa',
                    f'{equipoventa_ct.app_label}.delete_equipoventa',
                    f'{equipoventa_ct.app_label}.view_equipoventa',
                ]
            },

            # 2. JERARQUÍA DE VENTAS
            {
                'group_name': 'Jerarquía de Ventas',
                'navigation': {
                    'name': 'Jerarquía de Ventas',
                    'url': '/sales/equipos/',
                    'icon': 'fas fa-sitemap',
                    'order': 20,
                    'category': category
                },
                'permissions': [
                    f'{gerenteequipo_ct.app_label}.add_gerenteequipo',
                    f'{gerenteequipo_ct.app_label}.change_gerenteequipo',
                    f'{gerenteequipo_ct.app_label}.delete_gerenteequipo',
                    f'{gerenteequipo_ct.app_label}.view_gerenteequipo',
                    f'{jefeventa_ct.app_label}.add_jefeventa',
                    f'{jefeventa_ct.app_label}.change_jefeventa',
                    f'{jefeventa_ct.app_label}.delete_jefeventa',
                    f'{jefeventa_ct.app_label}.view_jefeventa',
                    f'{teamleader_ct.app_label}.add_teamleader',
                    f'{teamleader_ct.app_label}.change_teamleader',
                    f'{teamleader_ct.app_label}.delete_teamleader',
                    f'{teamleader_ct.app_label}.view_teamleader',
                    f'{vendedor_ct.app_label}.add_vendedor',
                    f'{vendedor_ct.app_label}.change_vendedor',
                    f'{vendedor_ct.app_label}.delete_vendedor',
                    f'{vendedor_ct.app_label}.view_vendedor',
                ]
            },

            # 3. ASIGNACIÓN PROYECTO-EQUIPO
            {
                'group_name': 'Asignación Proyecto-Equipo',
                'navigation': {
                    'name': 'Asignaciones',
                    'url': '/sales/equipos/',
                    'icon': 'fas fa-link',
                    'order': 30,
                    'category': category
                },
                'permissions': [
                    f'{asignacion_ct.app_label}.add_asignacionequipoproyecto',
                    f'{asignacion_ct.app_label}.change_asignacionequipoproyecto',
                    f'{asignacion_ct.app_label}.delete_asignacionequipoproyecto',
                    f'{asignacion_ct.app_label}.view_asignacionequipoproyecto',
                    f'{equipoventa_ct.app_label}.view_equipoventa',
                ]
            },

            # 4. DASHBOARD DE VENTAS
            {
                'group_name': 'Dashboard de Ventas',
                'navigation': {
                    'name': 'Dashboard Ventas',
                    'url': '/sales/',
                    'icon': 'fas fa-tachometer-alt',
                    'order': 40,
                    'category': category
                },
                'permissions': [
                    f'{equipoventa_ct.app_label}.view_equipoventa',
                    f'{vendedor_ct.app_label}.view_vendedor',
                ]
            }
        ]

        return self.create_modules(modules_config)

    def create_leads_modules(self, category):
        """Crea los módulos de LEADS & CRM"""
        self.stdout.write("\n📦 Creando módulos de LEADS & CRM...")

        # Nota: Estos modelos aún no existen, pero los preparamos para cuando se implementen
        modules_config = [
            # 1. GESTIÓN DE CAMPAÑAS
            {
                'group_name': 'Gestión de Campañas',
                'navigation': {
                    'name': 'Campañas',
                    'url': '/sales/campanas/',
                    'icon': 'fas fa-bullhorn',
                    'order': 10,
                    'category': category
                },
                'permissions': []  # Se agregaran cuando se implementen los modelos
            },

            # 2. GESTIÓN DE LEADS
            {
                'group_name': 'Gestión de Leads',
                'navigation': {
                    'name': 'Leads',
                    'url': '/sales/leads/',
                    'icon': 'fas fa-user-plus',
                    'order': 20,
                    'category': category
                },
                'permissions': []  # Se agregaran cuando se implementen los modelos
            },

            # 3. PROCESO DE VENTA
            {
                'group_name': 'Proceso de Venta',
                'navigation': {
                    'name': 'Procesos de Venta',
                    'url': '/sales/procesos/',
                    'icon': 'fas fa-funnel-dollar',
                    'order': 30,
                    'category': category
                },
                'permissions': []  # Se agregaran cuando se implementen los modelos
            },

            # 4. COTIZACIONES
            {
                'group_name': 'Cotizaciones',
                'navigation': {
                    'name': 'Cotizaciones',
                    'url': '/sales/cotizaciones/',
                    'icon': 'fas fa-file-invoice-dollar',
                    'order': 40,
                    'category': category
                },
                'permissions': []  # Se agregaran cuando se implementen los modelos
            },

            # 5. DASHBOARD CRM
            {
                'group_name': 'Dashboard CRM',
                'navigation': {
                    'name': 'Dashboard CRM',
                    'url': '/sales/crm/',
                    'icon': 'fas fa-chart-pie',
                    'order': 50,
                    'category': category
                },
                'permissions': []  # Se agregaran cuando se implementen los modelos
            }
        ]

        return self.create_modules(modules_config)

    def create_commissions_modules(self, category):
        """Crea los módulos de COMISIONES"""
        self.stdout.write("\n📦 Creando módulos de COMISIONES...")

        # Obtener content types
        comisiondesarrollo_ct = ContentType.objects.get_for_model(ComisionDesarrollo)
        comisionventa_ct = ContentType.objects.get_for_model(ComisionVenta)

        modules_config = [
            # 1. COMISIONES DE DESARROLLO
            {
                'group_name': 'Comisiones de Desarrollo',
                'navigation': {
                    'name': 'Comisiones Desarrollo',
                    'url': '/sales/proyectos/',
                    'icon': 'fas fa-building',
                    'order': 10,
                    'category': category
                },
                'permissions': [
                    f'{comisiondesarrollo_ct.app_label}.add_comisiondesarrollo',
                    f'{comisiondesarrollo_ct.app_label}.change_comisiondesarrollo',
                    f'{comisiondesarrollo_ct.app_label}.delete_comisiondesarrollo',
                    f'{comisiondesarrollo_ct.app_label}.view_comisiondesarrollo',
                ]
            },

            # 2. COMISIONES DE VENTA
            {
                'group_name': 'Comisiones de Venta',
                'navigation': {
                    'name': 'Comisiones Venta',
                    'url': '/sales/equipos/',
                    'icon': 'fas fa-users',
                    'order': 20,
                    'category': category
                },
                'permissions': [
                    f'{comisionventa_ct.app_label}.add_comisionventa',
                    f'{comisionventa_ct.app_label}.change_comisionventa',
                    f'{comisionventa_ct.app_label}.delete_comisionventa',
                    f'{comisionventa_ct.app_label}.view_comisionventa',
                ]
            },

            # 3. COMISIONES GENERADAS
            {
                'group_name': 'Comisiones Generadas',
                'navigation': {
                    'name': 'Comisiones Generadas',
                    'url': '/sales/comisiones/',
                    'icon': 'fas fa-dollar-sign',
                    'order': 30,
                    'category': category
                },
                'permissions': []  # Se agregaran cuando se implemente ComisionGenerada
            },

            # 4. REPORTES DE COMISIONES
            {
                'group_name': 'Reportes de Comisiones',
                'navigation': {
                    'name': 'Reportes',
                    'url': '/sales/reportes/',
                    'icon': 'fas fa-chart-line',
                    'order': 40,
                    'category': category
                },
                'permissions': [
                    f'{comisiondesarrollo_ct.app_label}.view_comisiondesarrollo',
                    f'{comisionventa_ct.app_label}.view_comisionventa',
                ]
            }
        ]

        return self.create_modules(modules_config)

    def create_modules(self, modules_config):
        """Crea los módulos basado en la configuración"""
        created_groups = []

        for module_data in modules_config:
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
        """Asigna todos los módulos al rol de superadmin"""
        self.stdout.write("\n👑 Asignando módulos al Super Administrador...")
        
        try:
            superadmin_role = Role.objects.get(name='Super Administrador')

            # Obtener todos los módulos creados
            all_modules = Group.objects.filter(
                name__in=[
                    # Desarrollo
                    'Gestión de Proyectos',
                    'Gestión de Inmuebles', 
                    'Roles de Desarrollo',
                    'Dashboard de Proyectos',
                    
                    # Ventas
                    'Gestión de Equipos de Venta',
                    'Jerarquía de Ventas',
                    'Asignación Proyecto-Equipo',
                    'Dashboard de Ventas',
                    
                    # Leads & CRM
                    'Gestión de Campañas',
                    'Gestión de Leads',
                    'Proceso de Venta',
                    'Cotizaciones',
                    'Dashboard CRM',
                    
                    # Comisiones
                    'Comisiones de Desarrollo',
                    'Comisiones de Venta',
                    'Comisiones Generadas',
                    'Reportes de Comisiones'
                ]
            )

            # Agregar módulos al rol existente (no reemplazar)
            current_groups = list(superadmin_role.groups.all())
            new_groups = current_groups + list(all_modules)
            superadmin_role.groups.set(new_groups)

            self.stdout.write(
                f"  📦 {all_modules.count()} módulos del sistema completo asignados al superadmin"
            )

        except Role.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('  ⚠️ Rol "Super Administrador" no encontrado')
            )