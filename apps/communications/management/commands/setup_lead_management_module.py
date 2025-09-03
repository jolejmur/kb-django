# apps/communications/management/commands/setup_lead_management_module.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from apps.accounts.models import MenuCategory, Navigation


class Command(BaseCommand):
    help = 'Configura el módulo "Gestión de Leads" en el sidebar del admin con URL mejorada'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('Configurando módulo "Gestión de Leads"...'))
            
            # 1. Crear o obtener categoría Gestión de Leads
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
            
            if created:
                self.stdout.write(f'✓ Categoría "{crm_category.name}" creada')
            else:
                self.stdout.write(f'○ Categoría "{crm_category.name}" ya existe')
            
            # 2. Crear grupo/módulo para Gestión de Leads
            lead_management_group, created = Group.objects.get_or_create(
                name='Gestión de Leads'
            )
            
            if created:
                self.stdout.write(f'✓ Grupo "{lead_management_group.name}" creado')
            else:
                self.stdout.write(f'○ Grupo "{lead_management_group.name}" ya existe')
            
            # 3. Crear elemento de navegación
            navigation, created = Navigation.objects.get_or_create(
                group=lead_management_group,
                defaults={
                    'name': 'Gestión de Leads',
                    'url': '/leads/',
                    'icon': 'fas fa-chart-line',
                    'order': 10,
                    'category': crm_category,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'✓ Navegación "{navigation.name}" creada')
            else:
                # Actualizar URL si ya existe
                navigation.url = '/leads/'
                navigation.name = 'Gestión de Leads'
                navigation.icon = 'fas fa-chart-line'
                navigation.category = crm_category
                navigation.save()
                self.stdout.write(f'○ Navegación "{navigation.name}" actualizada')
            
            # 4. Configurar permisos
            from apps.communications.models import LeadDistributionConfig, LeadAssignment, Lead, Cliente
            
            permission_configs = [
                # Permisos para LeadDistributionConfig
                {
                    'model': LeadDistributionConfig,
                    'permissions': ['view', 'add', 'change', 'delete']
                },
                # Permisos para LeadAssignment
                {
                    'model': LeadAssignment,
                    'permissions': ['view', 'add', 'change', 'delete']
                },
                # Permisos para Lead
                {
                    'model': Lead,
                    'permissions': ['view', 'change']
                },
                # Permisos para Cliente
                {
                    'model': Cliente,
                    'permissions': ['view']
                },
            ]
            
            permissions = []
            for config in permission_configs:
                content_type = ContentType.objects.get_for_model(config['model'])
                for perm_type in config['permissions']:
                    codename = f"{perm_type}_{config['model']._meta.model_name}"
                    name = f"Can {perm_type} {config['model']._meta.verbose_name}"
                    
                    permission, created = Permission.objects.get_or_create(
                        content_type=content_type,
                        codename=codename,
                        defaults={'name': name}
                    )
                    permissions.append(permission)
                    
                    if created:
                        self.stdout.write(f'  ✓ Permiso "{codename}" creado')
            
            # 5. Asignar permisos al grupo
            current_permissions = set(lead_management_group.permissions.all())
            new_permissions = set(permissions)
            permissions_to_add = new_permissions - current_permissions
            
            if permissions_to_add:
                lead_management_group.permissions.add(*permissions_to_add)
                self.stdout.write(f'✓ {len(permissions_to_add)} permisos agregados al grupo')
            
            # 6. Agregar permisos a grupos relacionados
            related_groups = ['CRM', 'Comunicaciones', 'ADMINISTRADORES']
            for group_name in related_groups:
                try:
                    group = Group.objects.get(name=group_name)
                    group.permissions.add(*permissions)
                    self.stdout.write(f'✓ Permisos agregados al grupo "{group_name}"')
                except Group.DoesNotExist:
                    self.stdout.write(f'○ Grupo "{group_name}" no existe, saltando...')
            
            # 7. Mostrar resumen
            self.stdout.write('\n' + '='*60)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Módulo "Gestión de Leads" configurado exitosamente!'
                )
            )
            self.stdout.write(f'Categoría: {crm_category.name}')
            self.stdout.write(f'URL: {navigation.url}')
            self.stdout.write(f'Total permisos: {lead_management_group.permissions.count()}')
            
            # 8. URLs disponibles
            self.stdout.write('\n' + self.style.SUCCESS('URLs disponibles:'))
            self.stdout.write('- /leads/ (Panel principal desde sidebar)')
            self.stdout.write('- /marketing/lead-management/ (Dashboard principal)')
            self.stdout.write('- /marketing/lead-distribution/ (Configuración automática)')
            self.stdout.write('- /marketing/lead-distribution/manual/ (Asignación manual)')
            self.stdout.write('- /marketing/lead-distribution/history/ (Historial)')
            
            self.stdout.write('\n' + self.style.WARNING('Próximos pasos:'))
            self.stdout.write('1. Ejecutar: python manage.py setup_lead_management_module')
            self.stdout.write('2. Asignar el grupo "Gestión de Leads" a los usuarios correspondientes')
            self.stdout.write('3. Verificar que aparezca en el sidebar del admin')
            
            self.stdout.write('\n' + '='*60)