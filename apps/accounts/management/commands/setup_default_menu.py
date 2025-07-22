# apps/accounts/management/commands/setup_default_menu.py
# VERSIÓN FINAL - INTEGRA TODOS LOS FIXES

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from apps.accounts.models import MenuCategory, Navigation, Role

User = get_user_model()


class Command(BaseCommand):
    help = 'Configura un sistema básico con 4 grupos esenciales + fixes automáticos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Limpia completamente la base de datos antes de configurar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Configurando sistema básico con 4 grupos esenciales...'))

        # 1. Limpiar si se solicita
        if options['clean']:
            self.clean_database()

        # 2. Crear categoría de administración
        admin_category = self.create_admin_category()

        # 3. FIX: Corregir navegaciones sin categoría ANTES de crear grupos
        self.fix_navigation_categories(admin_category)

        # 4. Crear los 4 grupos básicos
        created_groups = self.create_basic_groups(admin_category)

        # 5. FIX: Verificar y corregir asignaciones después de crear grupos
        self.verify_and_fix_all_assignments(admin_category)

        # 6. Asignar TODOS los grupos al superadmin
        self.assign_to_superadmin(created_groups)

        self.stdout.write(
            self.style.SUCCESS('✅ Sistema básico configurado exitosamente con 4 grupos + fixes aplicados!')
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
            'description': 'Herramientas para administrar usuarios, roles, permisos y categorías',
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

    def fix_navigation_categories(self, admin_category):
        """FIX: Corrige navegaciones sin categoría asignada"""
        self.stdout.write("🔧 Aplicando fix de categorías...")

        # Obtener todos los elementos de navegación sin categoría
        navigation_without_category = Navigation.objects.filter(category__isnull=True)

        if navigation_without_category.exists():
            self.stdout.write(f"  🔍 Encontrados {navigation_without_category.count()} elementos sin categoría")

            # Asignar la categoría de administración a todos
            for nav in navigation_without_category:
                nav.category = admin_category
                nav.save()
                self.stdout.write(f"    ✅ Categoría asignada a: {nav.name}")
        else:
            self.stdout.write("  ✅ Todos los elementos de navegación ya tienen categoría asignada")

    def create_basic_groups(self, admin_category):
        """Crea los 4 grupos básicos del sistema"""

        # Obtener content types
        group_ct = ContentType.objects.get_for_model(Group)
        permission_ct = ContentType.objects.get_for_model(Permission)
        role_ct = ContentType.objects.get_for_model(Role)
        user_ct = ContentType.objects.get_for_model(User)
        category_ct = ContentType.objects.get_for_model(MenuCategory)
        navigation_ct = ContentType.objects.get_for_model(Navigation)

        # Definir los 4 grupos básicos
        basic_groups_config = [
            # 1. GESTIÓN DE CATEGORÍAS
            {
                'group_name': 'Gestión de Categorías',
                'navigation': {
                    'name': 'Categorías del Menú',
                    'url': '/accounts/admin/categories/',
                    'icon': 'fas fa-folder-open',
                    'order': 10,
                    'category': admin_category
                },
                'permissions': [
                    f'{category_ct.app_label}.add_menucategory',
                    f'{category_ct.app_label}.change_menucategory',
                    f'{category_ct.app_label}.delete_menucategory',
                    f'{category_ct.app_label}.view_menucategory',
                ]
            },

            # 2. GESTIÓN DE MÓDULOS
            {
                'group_name': 'Gestión de Módulos',
                'navigation': {
                    'name': 'Módulos del Sistema',
                    'url': '/accounts/admin/modules/',
                    'icon': 'fas fa-cubes',
                    'order': 20,
                    'category': admin_category
                },
                'permissions': [
                    f'{group_ct.app_label}.add_group',
                    f'{group_ct.app_label}.change_group',
                    f'{group_ct.app_label}.delete_group',
                    f'{group_ct.app_label}.view_group',
                    f'{permission_ct.app_label}.view_permission',
                    f'{navigation_ct.app_label}.add_navigation',
                    f'{navigation_ct.app_label}.change_navigation',
                    f'{navigation_ct.app_label}.delete_navigation',
                    f'{navigation_ct.app_label}.view_navigation',
                    f'{category_ct.app_label}.view_menucategory',
                ]
            },

            # 3. GESTIÓN DE ROLES
            {
                'group_name': 'Gestión de Roles',
                'navigation': {
                    'name': 'Roles de Usuario',
                    'url': '/accounts/admin/roles/',
                    'icon': 'fas fa-user-tag',
                    'order': 30,
                    'category': admin_category
                },
                'permissions': [
                    f'{role_ct.app_label}.add_role',
                    f'{role_ct.app_label}.change_role',
                    f'{role_ct.app_label}.delete_role',
                    f'{role_ct.app_label}.view_role',
                    f'{group_ct.app_label}.view_group',
                ]
            },

            # 4. GESTIÓN DE USUARIOS
            {
                'group_name': 'Gestión de Usuarios',
                'navigation': {
                    'name': 'Usuarios del Sistema',
                    'url': '/accounts/admin/users/',
                    'icon': 'fas fa-users',
                    'order': 40,
                    'category': admin_category
                },
                'permissions': [
                    f'{user_ct.app_label}.add_user',
                    f'{user_ct.app_label}.change_user',
                    f'{user_ct.app_label}.delete_user',
                    f'{user_ct.app_label}.view_user',
                    f'{role_ct.app_label}.view_role',
                ]
            }
        ]

        created_groups = []

        for module_data in basic_groups_config:
            # Crear grupo
            group, group_created = Group.objects.get_or_create(
                name=module_data['group_name']
            )

            if group_created:
                self.stdout.write(f"  ✅ Grupo creado: {group.name}")
            else:
                self.stdout.write(f"  ⏭️  Grupo ya existe: {group.name}")

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
                        self.style.WARNING(f"    ⚠️  Permiso no encontrado: {perm_codename}")
                    )

            if permissions_to_assign:
                group.permissions.set(permissions_to_assign)
                self.stdout.write(f"    📋 Asignados {len(permissions_to_assign)} permisos")

            # Crear navegación CON CATEGORÍA ASEGURADA
            navigation_data = module_data['navigation'].copy()
            navigation, nav_created = Navigation.objects.get_or_create(
                group=group,
                defaults=navigation_data
            )

            if nav_created:
                self.stdout.write(f"    🔗 Navegación creada: {navigation.name}")
            else:
                # Actualizar navegación existente Y ASEGURAR CATEGORÍA
                for key, value in navigation_data.items():
                    setattr(navigation, key, value)
                navigation.save()
                self.stdout.write(f"    🔄 Navegación actualizada: {navigation.name}")

        return created_groups

    def verify_and_fix_all_assignments(self, admin_category):
        """Verifica y corrige todas las asignaciones después de crear grupos"""
        self.stdout.write("🔍 Verificando y corrigiendo todas las asignaciones...")

        # Verificar que todos los grupos básicos tienen navegación con categoría
        basic_groups = ['Gestión de Categorías', 'Gestión de Módulos', 'Gestión de Roles', 'Gestión de Usuarios']

        for group_name in basic_groups:
            try:
                group = Group.objects.get(name=group_name)
                try:
                    navigation = group.navigation
                    if not navigation.category:
                        navigation.category = admin_category
                        navigation.save()
                        self.stdout.write(f"  ✅ Categoría corregida para: {group_name}")
                    else:
                        self.stdout.write(f"  ✅ {group_name} tiene categoría: {navigation.category.name}")
                except Navigation.DoesNotExist:
                    self.stdout.write(f"  ⚠️  {group_name} no tiene navegación (esto es anormal)")
            except Group.DoesNotExist:
                self.stdout.write(f"  ⚠️  Grupo no encontrado: {group_name}")

    def assign_to_superadmin(self, created_groups):
        """Asigna TODOS los grupos al rol de superadmin"""
        superadmins = User.objects.filter(is_superuser=True)

        if not superadmins.exists():
            self.stdout.write(
                self.style.WARNING('  ⚠️  No hay superadmins en el sistema')
            )
            return

        # Crear rol de superadmin (marcado como sistema)
        superadmin_role, created = Role.objects.get_or_create(
            name='Super Administrador',
            defaults={
                'description': 'Acceso completo a todas las funciones del sistema',
                'is_system': True
            }
        )

        if created:
            self.stdout.write(f"  ✅ Rol de superadmin creado: {superadmin_role.name}")
        else:
            # Asegurarse de que esté marcado como rol del sistema
            if not superadmin_role.is_system:
                superadmin_role.is_system = True
                superadmin_role.save()
            self.stdout.write(f"  ⏭️  Rol de superadmin ya existe: {superadmin_role.name}")

        # Obtener todos los grupos básicos por nombre
        all_basic_groups = Group.objects.filter(
            name__in=[
                'Gestión de Categorías',
                'Gestión de Módulos',
                'Gestión de Roles',
                'Gestión de Usuarios'
            ]
        )

        # Limpiar grupos actuales y asignar todos
        superadmin_role.groups.clear()
        superadmin_role.groups.set(all_basic_groups)

        self.stdout.write(
            f"  📦 Asignados {all_basic_groups.count()}/4 grupos básicos al rol de superadmin"
        )

        # Verificar que todos los grupos estén asignados
        assigned_groups = superadmin_role.groups.all()
        self.stdout.write(f"  ✅ Grupos asignados al superadmin:")
        for group in assigned_groups:
            self.stdout.write(f"     - {group.name}")

        # Verificar si faltan grupos
        if assigned_groups.count() < 4:
            self.stdout.write(
                self.style.WARNING(f"  ⚠️  Solo {assigned_groups.count()}/4 grupos asignados")
            )

        # Asignar el rol a todos los superadmins
        for superadmin in superadmins:
            superadmin.role = superadmin_role
            superadmin.save()
            self.stdout.write(
                f"  👤 Rol asignado a superadmin: {superadmin.username}"
            )