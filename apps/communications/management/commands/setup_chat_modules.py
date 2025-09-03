# apps/communications/management/commands/setup_chat_modules.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from apps.accounts.models import MenuCategory, Navigation


class Command(BaseCommand):
    help = 'Configura los módulos de Chat y Supervisión de Chat en el sidebar'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('Configurando módulos de Chat...'))
            
            # 1. Obtener categoría Gestión de Leads
            crm_category, created = MenuCategory.objects.get_or_create(
                name='GESTIÓN DE LEADS',
                defaults={
                    'description': 'Gestión de clientes, leads y comunicaciones',
                    'icon': 'fas fa-users',
                    'color': 'blue',
                    'order': 30,
                    'is_system': False,
                    'is_active': True
                }
            )
            
            self.stdout.write(f'✓ Categoría: {crm_category.name}')
            
            # 2. Crear grupo/módulo para Chat Vendedor
            chat_group, created = Group.objects.get_or_create(
                name='Chat Vendedor'
            )
            
            if created:
                self.stdout.write(f'✓ Grupo "Chat Vendedor" creado')
            else:
                self.stdout.write(f'○ Grupo "Chat Vendedor" ya existe')
            
            # 3. Crear grupo/módulo para Supervisión de Chat
            supervision_group, created = Group.objects.get_or_create(
                name='Supervisión de Chat'
            )
            
            if created:
                self.stdout.write(f'✓ Grupo "Supervisión de Chat" creado')
            else:
                self.stdout.write(f'○ Grupo "Supervisión de Chat" ya existe')
            
            # 4. Crear navegación para Chat Vendedor
            chat_navigation, created = Navigation.objects.get_or_create(
                group=chat_group,
                defaults={
                    'name': 'Chat',
                    'url': '/marketing/chat/',
                    'icon': 'fas fa-comments',
                    'order': 40,
                    'category': crm_category,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'✓ Navegación "Chat" creada')
            else:
                # Actualizar si ya existe
                chat_navigation.url = '/marketing/chat/'
                chat_navigation.name = 'Chat'
                chat_navigation.icon = 'fas fa-comments'
                chat_navigation.category = crm_category
                chat_navigation.order = 40
                chat_navigation.save()
                self.stdout.write(f'○ Navegación "Chat" actualizada')
            
            # 5. Crear navegación para Supervisión de Chat
            supervision_navigation, created = Navigation.objects.get_or_create(
                group=supervision_group,
                defaults={
                    'name': 'Supervisión de Chat',
                    'url': '/marketing/supervision-chat/',
                    'icon': 'fas fa-eye',
                    'order': 50,
                    'category': crm_category,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'✓ Navegación "Supervisión de Chat" creada')
            else:
                # Actualizar si ya existe
                supervision_navigation.url = '/marketing/supervision-chat/'
                supervision_navigation.name = 'Supervisión de Chat'
                supervision_navigation.icon = 'fas fa-eye'
                supervision_navigation.category = crm_category
                supervision_navigation.order = 50
                supervision_navigation.save()
                self.stdout.write(f'○ Navegación "Supervisión de Chat" actualizada')
            
            # 6. Configurar permisos básicos para chat
            from apps.communications.models import Conversacion, Mensaje, WhatsAppConfig
            
            # Permisos para Chat Vendedor (limitados)
            chat_permissions = []
            
            # Permisos para Supervisión (completos)
            supervision_permissions = []
            
            models_config = [
                {'model': Conversacion, 'chat_perms': ['view'], 'supervision_perms': ['view', 'change']},
                {'model': Mensaje, 'chat_perms': ['view', 'add'], 'supervision_perms': ['view', 'add', 'change']},
                {'model': WhatsAppConfig, 'chat_perms': [], 'supervision_perms': ['view']},
            ]
            
            for config in models_config:
                content_type = ContentType.objects.get_for_model(config['model'])
                
                # Permisos para Chat Vendedor
                for perm_type in config['chat_perms']:
                    codename = f"{perm_type}_{config['model']._meta.model_name}"
                    permission, created = Permission.objects.get_or_create(
                        content_type=content_type,
                        codename=codename,
                        defaults={'name': f"Can {perm_type} {config['model']._meta.verbose_name}"}
                    )
                    chat_permissions.append(permission)
                
                # Permisos para Supervisión
                for perm_type in config['supervision_perms']:
                    codename = f"{perm_type}_{config['model']._meta.model_name}"
                    permission, created = Permission.objects.get_or_create(
                        content_type=content_type,
                        codename=codename,
                        defaults={'name': f"Can {perm_type} {config['model']._meta.verbose_name}"}
                    )
                    supervision_permissions.append(permission)
            
            # 7. Asignar permisos a grupos
            if chat_permissions:
                chat_group.permissions.set(chat_permissions)
                self.stdout.write(f'✓ {len(chat_permissions)} permisos asignados a "Chat Vendedor"')
            
            if supervision_permissions:
                supervision_group.permissions.set(supervision_permissions)
                self.stdout.write(f'✓ {len(supervision_permissions)} permisos asignados a "Supervisión de Chat"')
            
            # 8. Agregar permisos a grupos de alto nivel
            admin_groups = ['ADMINISTRADORES', 'Super Admin']
            for group_name in admin_groups:
                try:
                    group = Group.objects.get(name=group_name)
                    group.permissions.add(*supervision_permissions)
                    self.stdout.write(f'✓ Permisos de supervisión agregados a "{group_name}"')
                except Group.DoesNotExist:
                    self.stdout.write(f'○ Grupo "{group_name}" no existe')
            
            # 9. Agregar chat básico a vendedores
            sales_groups = ['Ventas', 'Team Leader', 'Vendedor']
            for group_name in sales_groups:
                try:
                    group = Group.objects.get(name=group_name)
                    group.permissions.add(*chat_permissions)
                    self.stdout.write(f'✓ Permisos de chat agregados a "{group_name}"')
                except Group.DoesNotExist:
                    self.stdout.write(f'○ Grupo "{group_name}" no existe')
            
            # 10. Mostrar resumen
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('Módulos de Chat configurados exitosamente!'))
            self.stdout.write(f'Categoría: {crm_category.name}')
            self.stdout.write('\nNuevas entradas en sidebar:')
            self.stdout.write(f'  📱 Chat: {chat_navigation.url}')
            self.stdout.write(f'  👁️  Supervisión: {supervision_navigation.url}')
            
            self.stdout.write('\n' + self.style.SUCCESS('Control de acceso:'))
            self.stdout.write('  • Vendedores: Solo ven sus leads asignados')
            self.stdout.write('  • Team Leaders: Supervisión de su equipo')
            self.stdout.write('  • Administradores: Supervisión completa')
            
            self.stdout.write('\n' + '='*60)