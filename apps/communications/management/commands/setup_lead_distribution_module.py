# apps/communications/management/commands/setup_lead_distribution_module.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction


class Command(BaseCommand):
    help = 'Configura el módulo de Distribución de Leads con sus permisos correspondientes'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('Configurando módulo "Distribución de Leads"...'))
            
            # Crear grupo/módulo para Distribución de Leads
            lead_distribution_group, created = Group.objects.get_or_create(
                name='Distribución de Leads'
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Grupo "{lead_distribution_group.name}" creado')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ Grupo "{lead_distribution_group.name}" ya existe')
                )
            
            # Obtener content types para los modelos de communications
            from apps.communications.models import LeadDistributionConfig, LeadAssignment, Lead, Cliente
            
            content_types = [
                ContentType.objects.get_for_model(LeadDistributionConfig),
                ContentType.objects.get_for_model(LeadAssignment),
                ContentType.objects.get_for_model(Lead),
                ContentType.objects.get_for_model(Cliente),
            ]
            
            # Definir permisos específicos para el módulo
            permission_configs = [
                # Permisos para LeadDistributionConfig
                {
                    'content_type': ContentType.objects.get_for_model(LeadDistributionConfig),
                    'codename': 'view_leaddistributionconfig',
                    'name': 'Can view lead distribution config'
                },
                {
                    'content_type': ContentType.objects.get_for_model(LeadDistributionConfig),
                    'codename': 'change_leaddistributionconfig',
                    'name': 'Can change lead distribution config'
                },
                {
                    'content_type': ContentType.objects.get_for_model(LeadDistributionConfig),
                    'codename': 'add_leaddistributionconfig',
                    'name': 'Can add lead distribution config'
                },
                {
                    'content_type': ContentType.objects.get_for_model(LeadDistributionConfig),
                    'codename': 'delete_leaddistributionconfig',
                    'name': 'Can delete lead distribution config'
                },
                
                # Permisos para LeadAssignment
                {
                    'content_type': ContentType.objects.get_for_model(LeadAssignment),
                    'codename': 'view_leadassignment',
                    'name': 'Can view lead assignment'
                },
                {
                    'content_type': ContentType.objects.get_for_model(LeadAssignment),
                    'codename': 'change_leadassignment',
                    'name': 'Can change lead assignment'
                },
                {
                    'content_type': ContentType.objects.get_for_model(LeadAssignment),
                    'codename': 'add_leadassignment',
                    'name': 'Can add lead assignment'
                },
                {
                    'content_type': ContentType.objects.get_for_model(LeadAssignment),
                    'codename': 'delete_leadassignment',
                    'name': 'Can delete lead assignment'
                },
                
                # Permisos para Lead (lectura principalmente)
                {
                    'content_type': ContentType.objects.get_for_model(Lead),
                    'codename': 'view_lead',
                    'name': 'Can view lead'
                },
                {
                    'content_type': ContentType.objects.get_for_model(Lead),
                    'codename': 'change_lead',
                    'name': 'Can change lead'
                },
                
                # Permisos para Cliente (lectura principalmente)  
                {
                    'content_type': ContentType.objects.get_for_model(Cliente),
                    'codename': 'view_cliente',
                    'name': 'Can view cliente'
                },
            ]
            
            # Crear o obtener permisos
            permissions = []
            for perm_config in permission_configs:
                permission, created = Permission.objects.get_or_create(
                    content_type=perm_config['content_type'],
                    codename=perm_config['codename'],
                    defaults={'name': perm_config['name']}
                )
                permissions.append(permission)
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Permiso "{permission.codename}" creado')
                    )
            
            # Asignar permisos al grupo
            current_permissions = set(lead_distribution_group.permissions.all())
            new_permissions = set(permissions)
            
            # Agregar permisos faltantes
            permissions_to_add = new_permissions - current_permissions
            if permissions_to_add:
                lead_distribution_group.permissions.add(*permissions_to_add)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {len(permissions_to_add)} permisos agregados al grupo')
                )
            
            # También agregar al grupo de Comunicaciones si existe
            try:
                communications_group = Group.objects.get(name='Comunicaciones')
                communications_group.permissions.add(*permissions)
                self.stdout.write(
                    self.style.SUCCESS('✓ Permisos agregados al grupo "Comunicaciones"')
                )
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING('○ Grupo "Comunicaciones" no existe, saltando...')
                )
            
            # También agregar al grupo CRM si existe
            try:
                crm_group = Group.objects.get(name='CRM')
                crm_group.permissions.add(*permissions)
                self.stdout.write(
                    self.style.SUCCESS('✓ Permisos agregados al grupo "CRM"')
                )
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING('○ Grupo "CRM" no existe, saltando...')
                )
            
            # Mostrar resumen
            total_permissions = lead_distribution_group.permissions.count()
            self.stdout.write('\n' + '='*50)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Módulo "Distribución de Leads" configurado exitosamente!'
                )
            )
            self.stdout.write(f'Total de permisos asignados: {total_permissions}')
            
            # Sugerencias para el administrador
            self.stdout.write('\n' + self.style.SUCCESS('Próximos pasos:'))
            self.stdout.write('1. Asignar el grupo "Distribución de Leads" a los roles que lo necesiten')
            self.stdout.write('2. Verificar que las fuerzas de venta estén configuradas correctamente')
            self.stdout.write('3. Configurar los porcentajes de distribución desde la interfaz web')
            
            self.stdout.write('\n' + self.style.SUCCESS('URLs disponibles:'))
            self.stdout.write('- /communications/lead-distribution/ (Configuración)')
            self.stdout.write('- /communications/lead-distribution/history/ (Historial)')
            
            self.stdout.write('\n' + '='*50)