"""
Management command to setup granular permissions for sales team management
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import Role


class Command(BaseCommand):
    help = 'Setup granular permissions for sales team management'

    def handle(self, *args, **options):
        self.stdout.write('Setting up granular permissions...')
        
        # Define permission groups with specific access levels
        permission_groups = {
            'Equipos - Solo Vista': {
                'permissions': [
                    'sales_team_management.view_organizationalunit',
                    'sales_team_management.view_teammembership',
                ],
                'description': 'Solo puede ver equipos y miembros'
            },
            'Equipos - Gestión Básica': {
                'permissions': [
                    'sales_team_management.view_organizationalunit',
                    'sales_team_management.add_organizationalunit',
                    'sales_team_management.change_organizationalunit',
                    'sales_team_management.view_teammembership',
                    'sales_team_management.add_teammembership',
                    'sales_team_management.change_teammembership',
                ],
                'description': 'Puede gestionar equipos y miembros básicamente'
            },
            'Jerarquía - Solo Vista': {
                'permissions': [
                    'sales_team_management.view_hierarchyrelation',
                ],
                'description': 'Solo puede ver relaciones jerárquicas'
            },
            'Jerarquía - Gestión Completa': {
                'permissions': [
                    'sales_team_management.view_hierarchyrelation',
                    'sales_team_management.add_hierarchyrelation',
                    'sales_team_management.change_hierarchyrelation',
                    'sales_team_management.delete_hierarchyrelation',
                ],
                'description': 'Puede gestionar completamente las jerarquías'
            },
            'Comisiones - Solo Vista': {
                'permissions': [
                    'sales_team_management.view_commissionstructure',
                ],
                'description': 'Solo puede ver estructuras de comisiones'
            },
            'Comisiones - Gestión Completa': {
                'permissions': [
                    'sales_team_management.view_commissionstructure',
                    'sales_team_management.add_commissionstructure',
                    'sales_team_management.change_commissionstructure',
                    'sales_team_management.delete_commissionstructure',
                ],
                'description': 'Puede gestionar completamente las comisiones'
            },
        }
        
        # Create or update permission groups
        created_groups = []
        for group_name, group_data in permission_groups.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_groups.append(group_name)
                self.stdout.write(f'  ✓ Created group: {group_name}')
            else:
                self.stdout.write(f'  → Updated group: {group_name}')
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add specified permissions
            for perm_string in group_data['permissions']:
                try:
                    app_label, codename = perm_string.split('.')
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    group.permissions.add(permission)
                    self.stdout.write(f'    + Added permission: {codename}')
                except Permission.DoesNotExist:
                    self.stdout.write(
                        f'    ! Permission not found: {perm_string}',
                        self.style.WARNING
                    )
                except ValueError:
                    self.stdout.write(
                        f'    ! Invalid permission format: {perm_string}',
                        self.style.ERROR
                    )
        
        # Define role configurations
        role_configurations = {
            'Gerente de Equipo': {
                'groups': ['Equipos - Gestión Básica'],  # Solo equipos, NO jerarquía ni comisiones
                'description': 'Puede gestionar equipos y miembros, pero no jerarquías ni comisiones'
            },
            'Gerente de Proyecto': {
                'groups': ['Equipos - Gestión Básica', 'Jerarquía - Solo Vista'],
                'description': 'Puede gestionar equipos y ver jerarquías'
            },
            'Super Admin': {
                'groups': [
                    'Equipos - Gestión Básica', 
                    'Jerarquía - Gestión Completa', 
                    'Comisiones - Gestión Completa'
                ],
                'description': 'Acceso completo a todo'
            },
            'Registro': {
                'groups': [
                    'Equipos - Gestión Básica', 
                    'Jerarquía - Gestión Completa', 
                    'Comisiones - Gestión Completa'
                ],
                'description': 'Acceso completo para gestión administrativa'
            },
        }
        
        # Configure roles
        self.stdout.write('\nConfiguring roles...')
        for role_name, role_config in role_configurations.items():
            try:
                role = Role.objects.get(name=role_name)
                
                # Remove all current groups from role
                role.groups.clear()
                
                # Add specified groups
                for group_name in role_config['groups']:
                    try:
                        group = Group.objects.get(name=group_name)
                        role.groups.add(group)
                        self.stdout.write(f'  ✓ Added group "{group_name}" to role "{role_name}"')
                    except Group.DoesNotExist:
                        self.stdout.write(
                            f'  ! Group not found: {group_name}',
                            self.style.WARNING
                        )
                
                self.stdout.write(f'  → Role "{role_name}": {role_config["description"]}')
                
            except Role.DoesNotExist:
                self.stdout.write(
                    f'  ! Role not found: {role_name}',
                    self.style.WARNING
                )
        
        # Clean up old broad permissions group from roles that shouldn't have it
        try:
            broad_group = Group.objects.get(name='Gestión de Equipos')
            roles_with_broad = Role.objects.filter(groups=broad_group).exclude(
                name__in=['Super Admin', 'Registro']
            )
            
            for role in roles_with_broad:
                role.groups.remove(broad_group)
                self.stdout.write(f'  → Removed broad permissions from: {role.name}')
                
        except Group.DoesNotExist:
            pass
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Granular permissions setup completed successfully!')
        )
        
        # Show summary
        self.stdout.write('\n📋 Summary:')
        for role_name, role_config in role_configurations.items():
            try:
                role = Role.objects.get(name=role_name)
                user_count = role.users.count()
                self.stdout.write(f'  • {role_name}: {user_count} users - {role_config["description"]}')
            except Role.DoesNotExist:
                pass