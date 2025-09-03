"""
Management command to create specific module permissions without modifying existing ones
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from apps.sales_team_management.models import OrganizationalUnit


class Command(BaseCommand):
    help = 'Create specific module permissions for route access control'

    def handle(self, *args, **options):
        self.stdout.write('Creating specific module permissions...')
        
        # Get or create content type for module permissions
        content_type, created = ContentType.objects.get_or_create(
            app_label='sales_team_management',
            model='moduleaccess'  # Virtual model for module permissions
        )
        
        # Define module-specific permissions
        module_permissions = [
            {
                'codename': 'access_team_management_module',
                'name': 'Can access team management module',
                'description': 'Allows access to /sales/team-management/ routes'
            },
            {
                'codename': 'access_hierarchy_module', 
                'name': 'Can access hierarchy module',
                'description': 'Allows access to /sales/hierarchy/ routes'
            },
            {
                'codename': 'access_commissions_module',
                'name': 'Can access commissions module', 
                'description': 'Allows access to /sales/commissions/ routes'
            },
            {
                'codename': 'access_dashboard_module',
                'name': 'Can access dashboard module',
                'description': 'Allows access to /sales/dashboard/ routes'
            }
        ]
        
        created_permissions = []
        
        # Create permissions
        for perm_data in module_permissions:
            permission, created = Permission.objects.get_or_create(
                codename=perm_data['codename'],
                content_type=content_type,
                defaults={'name': perm_data['name']}
            )
            
            if created:
                created_permissions.append(perm_data['codename'])
                self.stdout.write(f'  ✓ Created: {perm_data["codename"]}')
            else:
                self.stdout.write(f'  → Exists: {perm_data["codename"]}')
        
        # Create groups for module access (without affecting existing groups)
        module_groups = [
            {
                'name': 'Team Management Access',
                'permissions': ['access_team_management_module']
            },
            {
                'name': 'Hierarchy Access',
                'permissions': ['access_hierarchy_module']
            },
            {
                'name': 'Commissions Access', 
                'permissions': ['access_commissions_module']
            },
            {
                'name': 'Dashboard Access',
                'permissions': ['access_dashboard_module']
            }
        ]
        
        created_groups = []
        
        for group_data in module_groups:
            group, created = Group.objects.get_or_create(name=group_data['name'])
            
            if created:
                created_groups.append(group_data['name'])
                self.stdout.write(f'  ✓ Created group: {group_data["name"]}')
            else:
                self.stdout.write(f'  → Group exists: {group_data["name"]}')
            
            # Add permissions to group
            for perm_codename in group_data['permissions']:
                try:
                    permission = Permission.objects.get(
                        codename=perm_codename,
                        content_type=content_type
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(f'    ! Permission not found: {perm_codename}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Module permissions system created!')
        )
        
        self.stdout.write('\n📋 Next steps:')
        self.stdout.write('1. Assign "Team Management Access" group to users who should access /sales/team-management/')
        self.stdout.write('2. Assign "Hierarchy Access" group to users who should access /sales/hierarchy/')
        self.stdout.write('3. Assign "Commissions Access" group to users who should access /sales/commissions/')
        
        self.stdout.write('\n⚠️  NOTE: This does NOT modify existing permissions or roles!')