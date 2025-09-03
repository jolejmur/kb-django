from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Elimina todos los usuarios excepto admin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la eliminación de usuarios',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'Este comando eliminará todos los usuarios excepto admin.\n'
                    'Usa --confirm para proceder.'
                )
            )
            return

        # Contar usuarios antes
        total_users = User.objects.count()
        users_to_delete = User.objects.exclude(username='admin').count()
        
        self.stdout.write(f'Usuarios totales: {total_users}')
        self.stdout.write(f'Usuarios a eliminar: {users_to_delete}')
        
        if users_to_delete == 0:
            self.stdout.write(self.style.SUCCESS('No hay usuarios para eliminar.'))
            return

        # Eliminar usuarios
        deleted_count, deleted_details = User.objects.exclude(username='admin').delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Eliminados {deleted_count} usuarios exitosamente.\n'
                f'Detalles: {deleted_details}'
            )
        )
        
        # Verificar usuarios restantes
        remaining_users = User.objects.all()
        self.stdout.write(f'Usuarios restantes: {remaining_users.count()}')
        for user in remaining_users:
            self.stdout.write(f'  - {user.username} ({user.email})')