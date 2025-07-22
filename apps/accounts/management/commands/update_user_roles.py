"""
Management command to update all user roles based on their hierarchical positions
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.signals import update_user_role

User = get_user_model()


class Command(BaseCommand):
    help = 'Update all user roles based on their hierarchical positions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Update role for specific user only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what changes would be made without applying them'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be applied')
            )
            self.stdout.write('=' * 50)

        if username:
            try:
                user = User.objects.get(username=username)
                users = [user]
                self.stdout.write(f'🎯 Updating role for user: {username}')
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ User "{username}" not found')
                )
                return
        else:
            users = User.objects.all()
            self.stdout.write(f'🎯 Updating roles for {users.count()} users')

        self.stdout.write('=' * 50)

        updated_count = 0
        unchanged_count = 0

        for user in users:
            old_role = user.role.name if user.role else 'Sin rol'
            
            # Get what the role should be
            from apps.accounts.signals import get_user_highest_role
            should_be_role = get_user_highest_role(user)
            
            if should_be_role:
                new_role_name = should_be_role
            else:
                new_role_name = 'Sin rol'

            if old_role != new_role_name:
                if not dry_run:
                    update_user_role(user)
                    updated_count += 1
                else:
                    updated_count += 1
                
                status = '🔄' if not dry_run else '🔍'
                self.stdout.write(
                    f'  {status} {user.username}: {old_role} → {new_role_name}'
                )
            else:
                unchanged_count += 1
                if options.get('verbosity', 1) >= 2:
                    self.stdout.write(
                        f'  ✅ {user.username}: {old_role} (sin cambios)'
                    )

        # Summary
        self.stdout.write('=' * 50)
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Roles updated successfully!\n'
                    f'   Updated: {updated_count} users\n'
                    f'   Unchanged: {unchanged_count} users'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'🔍 DRY RUN RESULTS:\n'
                    f'   Would update: {updated_count} users\n'
                    f'   Would remain unchanged: {unchanged_count} users\n'
                    f'\nRun without --dry-run to apply changes'
                )
            )

        # Show role distribution
        self.stdout.write('\n📊 Current role distribution:')
        from apps.accounts.models import Role
        
        for role in Role.objects.filter(is_active=True):
            count = User.objects.filter(role=role).count()
            if count > 0:
                self.stdout.write(f'   • {role.name}: {count} users')
        
        users_without_role = User.objects.filter(role__isnull=True).count()
        if users_without_role > 0:
            self.stdout.write(f'   • Sin rol: {users_without_role} users')