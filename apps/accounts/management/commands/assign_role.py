"""
Management command to assign roles to users
"""
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import User, Role


class Command(BaseCommand):
    help = 'Assign a role to a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user')
        parser.add_argument('role_name', type=str, help='Name of the role to assign')
        parser.add_argument(
            '--list-roles',
            action='store_true',
            help='List available roles'
        )

    def handle(self, *args, **options):
        if options['list_roles']:
            self.stdout.write(self.style.SUCCESS('Available roles:'))
            for role in Role.objects.filter(is_active=True):
                self.stdout.write(f'  - {role.name}: {role.description}')
            return

        username = options['username']
        role_name = options['role_name']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist.')

        try:
            role = Role.objects.get(name=role_name, is_active=True)
        except Role.DoesNotExist:
            raise CommandError(f'Role "{role_name}" does not exist or is inactive.')

        # Assign the role
        old_role = user.role.name if user.role else 'Sin rol'
        user.role = role
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully assigned role "{role.name}" to user "{user.username}"\n'
                f'Previous role: {old_role}'
            )
        )