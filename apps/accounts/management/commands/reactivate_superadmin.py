# apps/accounts/management/commands/reactivate_superadmin.py
# CREAR ESTE ARCHIVO NUEVO

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Reactiva todos los superadministradores del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Reactivar solo un superadmin específico por username',
        )

    def handle(self, *args, **options):
        username = options.get('username')

        if username:
            # Reactivar un superadmin específico
            try:
                user = User.objects.get(username=username, is_superuser=True)
                if not user.is_active:
                    user.is_active = True
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Superadmin "{username}" reactivado exitosamente')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Superadmin "{username}" ya está activo')
                    )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ No se encontró un superadmin con username "{username}"')
                )
        else:
            # Reactivar todos los superadmins
            inactive_superadmins = User.objects.filter(is_superuser=True, is_active=False)

            if inactive_superadmins.exists():
                count = inactive_superadmins.count()
                inactive_superadmins.update(is_active=True)

                self.stdout.write(
                    self.style.SUCCESS(f'✅ {count} superadministradores reactivados:')
                )

                for user in inactive_superadmins:
                    self.stdout.write(f'   - {user.username} ({user.email})')
            else:
                active_superadmins = User.objects.filter(is_superuser=True, is_active=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Todos los superadministradores ya están activos ({active_superadmins.count()} usuarios)')
                )

                for user in active_superadmins:
                    self.stdout.write(f'   - {user.username} ({user.email})')

        # Mostrar estado final
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 ESTADO ACTUAL DE SUPERADMINISTRADORES:")
        self.stdout.write("=" * 50)

        all_superadmins = User.objects.filter(is_superuser=True)
        active_count = all_superadmins.filter(is_active=True).count()
        inactive_count = all_superadmins.filter(is_active=False).count()

        self.stdout.write(f"✅ Activos: {active_count}")
        self.stdout.write(f"❌ Inactivos: {inactive_count}")
        self.stdout.write(f"📊 Total: {all_superadmins.count()}")

        if inactive_count > 0:
            self.stdout.write("\n⚠️  SUPERADMINS INACTIVOS:")
            for user in all_superadmins.filter(is_active=False):
                self.stdout.write(f"   - {user.username} ({user.email})")
            self.stdout.write(f"\n💡 Para reactivarlos: python manage.py reactivate_superadmin")

        self.stdout.write("=" * 50)