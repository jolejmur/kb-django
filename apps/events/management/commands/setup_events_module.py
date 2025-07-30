# apps/events/management/commands/setup_events_module.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from apps.accounts.models import MenuCategory, Navigation, Role
from apps.events.models import EventoComercial, InvitacionQR, VisitaEvento

User = get_user_model()


class Command(BaseCommand):
    help = 'Configura el módulo de eventos comerciales en el sistema de navegación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--assign-to-admin',
            action='store_true',
            help='Asigna automáticamente el módulo al rol de Super Administrador',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🎯 Configurando módulo de Eventos Comerciales...'))

        # 1. Crear o obtener la categoría de eventos
        events_category = self.create_events_category()

        # 2. Crear los grupos/módulos de eventos
        events_groups = self.create_events_group(events_category)

        # 3. Asignar al rol de administrador si se solicita
        if options['assign_to_admin']:
            self.assign_to_admin_role(events_groups)

        self.stdout.write(
            self.style.SUCCESS('✅ Módulo de Eventos Comerciales configurado exitosamente!')
        )

    def create_events_category(self):
        """Crea o obtiene la categoría de eventos comerciales"""
        category_data = {
            'name': 'EVENTOS COMERCIALES',
            'description': 'Gestión de eventos comerciales, invitaciones QR y seguimiento de visitas',
            'icon': 'fas fa-calendar-alt',
            'color': 'purple',
            'order': 50,
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
            self.stdout.write(f"  ⏭️  Categoría ya existe: {category.name}")

        return category

    def create_events_group(self, events_category):
        """Crea el grupo/módulo de eventos con todos sus permisos"""
        
        # Obtener content types
        evento_ct = ContentType.objects.get_for_model(EventoComercial)
        invitacion_ct = ContentType.objects.get_for_model(InvitacionQR)
        visita_ct = ContentType.objects.get_for_model(VisitaEvento)

        # Configuración de los módulos de eventos
        events_groups_config = [
            {
                'group_name': 'Gestión de Eventos Comerciales',
                'navigation': {
                    'name': 'Eventos Comerciales',
                    'url': '/events/',
                    'icon': 'fas fa-calendar-alt',
                    'order': 10,
                    'category': events_category
                },
                'permissions': [
                    # Permisos para EventoComercial
                    f'{evento_ct.app_label}.add_eventocomercial',
                    f'{evento_ct.app_label}.change_eventocomercial',
                    f'{evento_ct.app_label}.delete_eventocomercial',
                    f'{evento_ct.app_label}.view_eventocomercial',
                    
                    # Permisos para InvitacionQR
                    f'{invitacion_ct.app_label}.add_invitacionqr',
                    f'{invitacion_ct.app_label}.change_invitacionqr',
                    f'{invitacion_ct.app_label}.delete_invitacionqr',
                    f'{invitacion_ct.app_label}.view_invitacionqr',
                    
                    # Permisos para VisitaEvento
                    f'{visita_ct.app_label}.add_visitaevento',
                    f'{visita_ct.app_label}.change_visitaevento',
                    f'{visita_ct.app_label}.delete_visitaevento',
                    f'{visita_ct.app_label}.view_visitaevento',
                ]
            },
            {
                'group_name': 'Escáner QR de Eventos',
                'navigation': {
                    'name': 'Escáner QR',
                    'url': '/events/scanner/',
                    'icon': 'fas fa-qrcode',
                    'order': 20,
                    'category': events_category
                },
                'permissions': [
                    # Permisos para visualizar eventos y QRs
                    f'{evento_ct.app_label}.view_eventocomercial',
                    f'{invitacion_ct.app_label}.view_invitacionqr',
                    f'{visita_ct.app_label}.view_visitaevento',
                ]
            }
        ]

        created_groups = []

        for events_group_config in events_groups_config:
            # Crear grupo
            group, group_created = Group.objects.get_or_create(
                name=events_group_config['group_name']
            )

            if group_created:
                self.stdout.write(f"  ✅ Grupo creado: {group.name}")
            else:
                self.stdout.write(f"  ⏭️  Grupo ya existe: {group.name}")

            created_groups.append(group)

            # Limpiar y asignar permisos
            group.permissions.clear()
            permissions_to_assign = []

            for perm_codename in events_group_config['permissions']:
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
            navigation_data = events_group_config['navigation'].copy()
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

    def assign_to_admin_role(self, events_groups):
        """Asigna los módulos de eventos al rol de Super Administrador"""
        try:
            admin_role = Role.objects.get(name='Super Administrador')
            
            # Agregar todos los módulos de eventos a los grupos del rol
            for group in events_groups:
                admin_role.groups.add(group)
                self.stdout.write(
                    f"  👤 Módulo '{group.name}' asignado al rol: {admin_role.name}"
                )
            
            # Mostrar todos los grupos asignados
            assigned_groups = admin_role.groups.all()
            self.stdout.write(f"  ✅ Grupos en el rol Super Administrador:")
            for group in assigned_groups:
                self.stdout.write(f"     - {group.name}")
                
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.WARNING('  ⚠️  Rol "Super Administrador" no encontrado. Ejecuta primero setup_default_menu.')
            )