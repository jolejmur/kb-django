from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import MenuCategory, Navigation, Role


class Command(BaseCommand):
    help = 'Configura el módulo de reportes (groups) en el sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Limpia configuración existente antes de crear',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🏗️ Configurando módulo de Reportes...'))

        if options['clean']:
            self.clean_groups_module()

        # 1. Obtener categoría existente de GESTIÓN DE LEADS
        leads_category = self.get_leads_category()

        # 2. Crear módulo de reportes en la categoría de leads
        self.create_reports_module(leads_category)

        # 3. Asignar módulo al superadmin
        self.assign_to_superadmin()

        self.stdout.write(
            self.style.SUCCESS('✅ Módulo de Reportes configurado exitosamente!')
        )

    def clean_groups_module(self):
        """Limpia módulos de reportes existentes"""
        self.stdout.write("🧹 Limpiando módulo de reportes existente...")

        groups_modules = [
            'Reportes del Sistema',
            'Reportes de Leads',
        ]

        Group.objects.filter(name__in=groups_modules).delete()
        self.stdout.write("  🗑️ Módulo de reportes eliminado")

    def get_leads_category(self):
        """Obtiene la categoría existente de GESTIÓN DE LEADS"""
        try:
            category = MenuCategory.objects.get(name='GESTIÓN DE LEADS')
            self.stdout.write(f"  ✅ Usando categoría existente: {category.name}")
            return category
        except MenuCategory.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('  ❌ Categoría "GESTIÓN DE LEADS" no encontrada')
            )
            # Como fallback, crear la categoría
            category_data = {
                'name': 'GESTIÓN DE LEADS',
                'description': 'Gestión de leads y reportes relacionados',
                'icon': 'fas fa-user-plus',
                'color': 'blue',
                'order': 5,
                'is_system': False,
                'is_active': True
            }
            category = MenuCategory.objects.create(**category_data)
            self.stdout.write(f"  ✅ Categoría creada como fallback: {category.name}")
            return category

    def create_reports_module(self, reports_category):
        """Crea el módulo del sistema de reportes"""

        # Obtener content types necesarios para permisos básicos
        # Como el módulo de groups/reports no tiene modelos específicos,
        # usaremos permisos generales que le permitan ver reportes
        from django.contrib.auth.models import User
        user_ct = ContentType.objects.get_for_model(User)
        group_ct = ContentType.objects.get_for_model(Group)

        reports_module_config = {
            'group_name': 'Reportes de Leads',
            'navigation': {
                'name': 'Reportes de Leads',
                'url': '/reportes/',
                'icon': 'fas fa-chart-line',
                'order': 30,  # Después de otros módulos de leads
                'category': reports_category
            },
            'permissions': [
                # Permisos básicos para ver usuarios y grupos (necesarios para el reporte)
                'auth.view_group',
                # Estos permisos permiten acceder a la información necesaria para los reportes
            ]
        }

        # Crear grupo
        group, group_created = Group.objects.get_or_create(
            name=reports_module_config['group_name']
        )

        if group_created:
            self.stdout.write(f"  ✅ Módulo creado: {group.name}")
        else:
            self.stdout.write(f"  ⏭️ Módulo ya existe: {group.name}")

        # Limpiar y asignar permisos
        group.permissions.clear()
        permissions_to_assign = []

        for perm_codename in reports_module_config['permissions']:
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
        navigation_data = reports_module_config['navigation'].copy()
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

        return group

    def assign_to_superadmin(self):
        """Asigna el módulo de reportes al rol de superadmin"""
        try:
            superadmin_role = Role.objects.get(name='Super Admin')

            # Obtener módulo de reportes
            reports_module = Group.objects.get(name='Reportes de Leads')

            # Agregar módulo al rol existente (no reemplazar)
            current_groups = list(superadmin_role.groups.all())
            if reports_module not in current_groups:
                current_groups.append(reports_module)
                superadmin_role.groups.set(current_groups)
                
                self.stdout.write(
                    f"  📦 Módulo de Reportes asignado al superadmin"
                )
            else:
                self.stdout.write(
                    f"  ⏭️ Módulo de Reportes ya estaba asignado al superadmin"
                )

        except Role.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('  ⚠️ Rol "Super Administrador" no encontrado')
            )