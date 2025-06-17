# apps/accounts/management/commands/setup_default_menu.py
# REEMPLAZA COMPLETAMENTE el archivo existente

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from apps.accounts.models import MenuCategory, Navigation, Role

User = get_user_model()


class Command(BaseCommand):
    help = 'Configura un sistema básico con solo 3 grupos esenciales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Limpia completamente la base de datos antes de configurar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Configurando sistema básico con 3 grupos esenciales...'))

        # 1. Limpiar si se solicita
        if options['clean']:
            self.clean_database()

        # 2. Crear categoría de administración
        admin_category = self.create_admin_category()

        # 3. Crear los 3 grupos básicos
        self.create_basic_groups(admin_category)

        # 4. Asignar al superadmin
        self.assign_to_superadmin()

        self.stdout.write(
            self.style.SUCCESS('✅ Sistema básico configurado exitosamente con 3 grupos!')
        )

    def clean_database(self):
        """Limpia completamente grupos, roles y navegación"""
        self.stdout.write("🧹 Limpiando base de datos...")

        # Eliminar navegaciones
        Navigation.objects.all().delete()
        self.stdout.write("  🗑️  Navegaciones eliminadas")

        # Eliminar roles (esto también limpia asignaciones de usuarios)
        Role.objects.all().delete()
        self.stdout.write("  🗑️  Roles eliminados")

        # Eliminar grupos personalizados (mantener los de Django)
        custom_groups = Group.objects.exclude(
            name__in=['Staff', 'Superuser']  # Mantener grupos del sistema si existen
        )
        custom_groups.delete()
        self.stdout.write("  🗑️  Grupos personalizados eliminados")

        # Limpiar categorías personalizadas
        MenuCategory.objects.filter(is_system=False).delete()
        self.stdout.write("  🗑️  Categorías personalizadas eliminadas")

    def create_admin_category(self):
        """Crea la categoría de Administración del Sistema"""
        category_data = {
            'name': 'ADMINISTRACIÓN DEL SISTEMA',
            'description': 'Herramientas básicas para administrar usuarios, roles y permisos',
            'icon': 'fas fa-cogs',
            'color': 'red',
            'order': 10,
            'is_system': True,
            'is_active': True
        }

        category, created = MenuCategory.objects.get_or_create(
            name=category_data['name'],
            defaults=category_data
        )

        if created:
            self.stdout.write(f"  ✅ Categoría creada: {category.name}")
        else:
            self.stdout.write(f"  ⏭️  Categoría ya existe: {category.name}")

        return category

    def create_basic_groups(self, admin_category):
        """Crea los 3 grupos básicos del sistema"""

        # Obtener content types
        group_ct = ContentType.objects.get_for_model(Group)
        permission_ct = ContentType.objects.get_for_model(Permission)
        role_ct = ContentType.objects.get_for_model(Role)
        user_ct = ContentType.objects.get_for_model(User)
        category_ct = ContentType.objects.get_for_model(MenuCategory)
        navigation_ct = ContentType.objects.get_for_model(Navigation)

        # Definir los 3 grupos básicos
        basic_groups = [
            # 1. GESTIÓN DE MÓDULOS (Todo lo relacionado con Groups, Permissions, Navigation, Categories)
            {
                'group_name': 'Gestión de Módulos',
                'navigation': {
                    'name': 'Módulos del Sistema',
                    'url': '/accounts/admin/modules/',
                    'icon': 'fas fa-cubes',
                    'order': 10,
                    'category': admin_category
                },
                'permissions': [
                    # Groups (Módulos)
                    f'{group_ct.app_label}.add_group',
                    f'{group_ct.app_label}.change_group',
                    f'{group_ct.app_label}.delete_group',
                    f'{group_ct.app_label}.view_group',

                    # Permissions (para asignar a módulos)
                    f'{permission_ct.app_label}.view_permission',

                    # Navigation (elementos del menú)
                    f'{navigation_ct.app_label}.add_navigation',
                    f'{navigation_ct.app_label}.change_navigation',
                    f'{navigation_ct.app_label}.delete_navigation',
                    f'{navigation_ct.app_label}.view_navigation',

                    # Categories (categorías del menú)
                    f'{category_ct.app_label}.add_menucategory',
                    f'{category_ct.app_label}.change_menucategory',
                    f'{category_ct.app_label}.delete_menucategory',
                    f'{category_ct.app_label}.view_menucategory',
                ]
            },

            # 2. GESTIÓN DE ROLES (CRUD de roles + asignación de grupos a roles)
            {
                'group_name': 'Gestión de Roles',
                'navigation': {
                    'name': 'Roles de Usuario',
                    'url': '/accounts/admin/roles/',
                    'icon': 'fas fa-user-tag',
                    'order': 20,
                    'category': admin_category
                },
                'permissions': [
                    # Roles
                    f'{role_ct.app_label}.add_role',
                    f'{role_ct.app_label}.change_role',
                    f'{role_ct.app_label}.delete_role',
                    f'{role_ct.app_label}.view_role',

                    # Ver grupos para asignar a roles
                    f'{group_ct.app_label}.view_group',
                ]
            },

            # 3. GESTIÓN DE USUARIOS (CRUD de usuarios + asignación de roles a usuarios)
            {
                'group_name': 'Gestión de Usuarios',
                'navigation': {
                    'name': 'Usuarios del Sistema',
                    'url': '/accounts/admin/users/',
                    'icon': 'fas fa-users',
                    'order': 30,
                    'category': admin_category
                },
                'permissions': [
                    # Users
                    f'{user_ct.app_label}.add_user',
                    f'{user_ct.app_label}.change_user',
                    f'{user_ct.app_label}.delete_user',
                    f'{user_ct.app_label}.view_user',

                    # Ver roles para asignar a usuarios
                    f'{role_ct.app_label}.view_role',
                ]
            }
        ]

        for module_data in basic_groups:
            # Crear grupo
            group, group_created = Group.objects.get_or_create(
                name=module_data['group_name']
            )

            if group_created:
                self.stdout.write(f"  ✅ Grupo creado: {group.name}")
            else:
                self.stdout.write(f"  ⏭️  Grupo ya existe: {group.name}")

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
                        self.style.WARNING(f"    ⚠️  Permiso no encontrado: {perm_codename}")
                    )

            if permissions_to_assign:
                group.permissions.set(permissions_to_assign)
                self.stdout.write(f"    📋 Asignados {len(permissions_to_assign)} permisos")

            # Crear navegación
            navigation, nav_created = Navigation.objects.get_or_create(
                group=group,
                defaults=module_data['navigation']
            )

            if nav_created:
                self.stdout.write(f"    🔗 Navegación creada: {navigation.name}")
            else:
                # Actualizar navegación existente
                for key, value in module_data['navigation'].items():
                    setattr(navigation, key, value)
                navigation.save()
                self.stdout.write(f"    🔄 Navegación actualizada: {navigation.name}")

    def assign_to_superadmin(self):
        """Asigna todos los grupos al rol de superadmin"""
        superadmins = User.objects.filter(is_superuser=True)

        if not superadmins.exists():
            self.stdout.write(
                self.style.WARNING('  ⚠️  No hay superadmins en el sistema')
            )
            return

        # Crear rol de superadmin
        superadmin_role, created = Role.objects.get_or_create(
            name='Super Administrador',
            defaults={
                'description': 'Acceso completo a todas las funciones básicas del sistema'
            }
        )

        if created:
            self.stdout.write(f"  ✅ Rol de superadmin creado: {superadmin_role.name}")
        else:
            self.stdout.write(f"  ⏭️  Rol de superadmin ya existe: {superadmin_role.name}")

        # Asignar los 3 grupos básicos al rol de superadmin
        basic_groups = Group.objects.filter(
            name__in=['Gestión de Módulos', 'Gestión de Roles', 'Gestión de Usuarios']
        )
        superadmin_role.groups.set(basic_groups)

        self.stdout.write(
            f"  📦 Asignados {basic_groups.count()} grupos básicos al rol de superadmin"
        )

        # Asignar el rol a todos los superadmins
        for superadmin in superadmins:
            superadmin.role = superadmin_role
            superadmin.save()
            self.stdout.write(
                f"  👤 Rol asignado a superadmin: {superadmin.username}"
            )