# apps/communications/management/commands/delete_test_data_now.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.sales_team_management.models import OrganizationalUnit, TeamMembership
from apps.communications.models import LeadDistributionConfig, LeadAssignment

User = get_user_model()


class Command(BaseCommand):
    help = 'ELIMINA INMEDIATAMENTE los datos de prueba: Alpha, Beta, Gamma, test* y usuarios pepe, perez, carlos, rodrigues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar eliminación sin pregunta interactiva',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚨 ELIMINACIÓN INMEDIATA DE DATOS DE PRUEBA'))
        self.stdout.write('='*60)
        
        # Si no hay --confirm, pedir confirmación
        if not options['confirm']:
            confirm = input('❓ Esto eliminará PERMANENTEMENTE los datos de prueba. Escriba "ELIMINAR" para continuar: ')
            if confirm != 'ELIMINAR':
                self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                return

        try:
            with transaction.atomic():
                deleted_counts = {
                    'configs': 0,
                    'assignments': 0,
                    'memberships': 0,
                    'units': 0,
                    'users': 0
                }

                # 1. Buscar fuerzas de venta de prueba
                test_units = OrganizationalUnit.objects.filter(
                    unit_type='SALES'
                ).filter(
                    models.Q(name__icontains='alpha') |
                    models.Q(name__icontains='beta') |  
                    models.Q(name__icontains='gamma') |
                    models.Q(name__icontains='gama') |
                    models.Q(name__istartswith='test')
                )

                self.stdout.write(f'🎯 Encontradas {test_units.count()} fuerzas de venta de prueba:')
                for unit in test_units:
                    self.stdout.write(f'  • {unit.name} ({unit.code})')

                # 2. Buscar usuarios de prueba
                test_users = User.objects.filter(
                    username__in=['pepe', 'perez', 'carlos', 'rodrigues']
                )

                self.stdout.write(f'👥 Encontrados {test_users.count()} usuarios de prueba:')
                for user in test_users:
                    self.stdout.write(f'  • {user.username} ({user.get_full_name()})')

                if not test_units.exists() and not test_users.exists():
                    self.stdout.write(self.style.SUCCESS('✅ No hay datos de prueba para eliminar'))
                    return

                # 3. ELIMINACIÓN EN CASCADA
                self.stdout.write('\n🗑️  INICIANDO ELIMINACIÓN...')

                # Eliminar configuraciones de leads
                for unit in test_units:
                    configs = LeadDistributionConfig.objects.filter(organizational_unit=unit)
                    count = configs.count()
                    if count > 0:
                        configs.delete()
                        deleted_counts['configs'] += count
                        self.stdout.write(f'  ✅ {count} configs eliminadas de {unit.name}')

                # Eliminar asignaciones de leads  
                for unit in test_units:
                    assignments = LeadAssignment.objects.filter(organizational_unit=unit)
                    count = assignments.count()
                    if count > 0:
                        assignments.delete()
                        deleted_counts['assignments'] += count
                        self.stdout.write(f'  ✅ {count} asignaciones eliminadas de {unit.name}')

                # Eliminar membresías
                for unit in test_units:
                    memberships = TeamMembership.objects.filter(organizational_unit=unit)
                    count = memberships.count()
                    if count > 0:
                        memberships.delete()
                        deleted_counts['memberships'] += count
                        self.stdout.write(f'  ✅ {count} membresías eliminadas de {unit.name}')

                # Eliminar fuerzas de venta
                for unit in test_units:
                    name = unit.name
                    unit.delete()
                    deleted_counts['units'] += 1
                    self.stdout.write(f'  🗑️  Fuerza "{name}" ELIMINADA')

                # Eliminar usuarios
                for user in test_users:
                    username = user.username
                    full_name = user.get_full_name()
                    user.delete()
                    deleted_counts['users'] += 1
                    self.stdout.write(f'  👤 Usuario "{username}" ({full_name}) ELIMINADO')

                # RESUMEN FINAL
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('✅ ELIMINACIÓN COMPLETADA'))
                self.stdout.write('='*60)
                self.stdout.write(f'📊 ELEMENTOS ELIMINADOS:')
                self.stdout.write(f'  • {deleted_counts["configs"]} configuraciones de leads')
                self.stdout.write(f'  • {deleted_counts["assignments"]} asignaciones de leads')
                self.stdout.write(f'  • {deleted_counts["memberships"]} membresías de equipos')
                self.stdout.write(f'  • {deleted_counts["units"]} fuerzas de venta')
                self.stdout.write(f'  • {deleted_counts["users"]} usuarios')

                # Mostrar estado final
                remaining = OrganizationalUnit.objects.filter(unit_type='SALES', is_active=True)
                self.stdout.write(f'\n🏢 FUERZAS DE VENTA ACTIVAS RESTANTES: {remaining.count()}')
                for unit in remaining.order_by('name'):
                    members = unit.teammembership_set.filter(is_active=True).count()
                    self.stdout.write(f'  ✅ {unit.name} - {members} miembros')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ ERROR: {str(e)}'))
            raise

# Importar Q para las queries
from django.db import models