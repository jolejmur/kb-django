# apps/communications/management/commands/fix_manager_permissions.py
from django.core.management.base import BaseCommand, CommandError
from apps.sales_team_management.models import TeamMembership, PositionType, OrganizationalUnit
from apps.accounts.models import User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica y arregla los permisos de gerentes de equipo para acceso a lead management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Aplicar correcciones automáticamente',
        )
        parser.add_argument(
            '--team',
            type=str,
            help='Filtrar por nombre de equipo específico',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== VERIFICACIÓN DE PERMISOS DE GERENTES DE EQUIPO ===\n'))
        
        # Obtener todos los equipos de ventas
        teams_query = OrganizationalUnit.objects.filter(unit_type='SALES', is_active=True)
        
        if options['team']:
            teams_query = teams_query.filter(name__icontains=options['team'])
            
        teams = teams_query.order_by('name')
        
        if not teams:
            self.stdout.write(self.style.ERROR('No se encontraron equipos de ventas.'))
            return

        # Buscar o crear position_type para gerentes
        manager_position, created = PositionType.objects.get_or_create(
            name='Gerente de Equipo',
            defaults={
                'description': 'Gerente de Equipo de Ventas',
                'is_manager': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Creado position_type: {manager_position.name}'))
        
        total_fixed = 0
        
        for team in teams:
            self.stdout.write(f'\n📋 EQUIPO: {team.name}')
            self.stdout.write('-' * 50)
            
            # Obtener todos los miembros activos del equipo
            members = TeamMembership.objects.filter(
                organizational_unit=team,
                is_active=True
            ).select_related('user', 'position_type')
            
            if not members:
                self.stdout.write(self.style.WARNING('  ⚠️  Sin miembros activos'))
                continue
                
            # Buscar posibles gerentes (por nombre de usuario, email o position_type existente)
            potential_managers = []
            regular_members = []
            
            for member in members:
                user = member.user
                is_manager = False
                
                # Criterios para identificar gerentes
                if (
                    'gerente' in user.get_full_name().lower() or
                    'gerente' in user.username.lower() or
                    'manager' in user.username.lower() or
                    (member.position_type and 'gerente' in member.position_type.name.lower())
                ):
                    is_manager = True
                
                if is_manager:
                    potential_managers.append(member)
                else:
                    regular_members.append(member)
            
            # Mostrar estado actual
            self.stdout.write(f'  👥 Total miembros: {len(members)}')
            self.stdout.write(f'  👨‍💼 Gerentes identificados: {len(potential_managers)}')
            self.stdout.write(f'  👤 Miembros regulares: {len(regular_members)}')
            
            # Listar miembros
            for member in members:
                user = member.user
                position_name = member.position_type.name if member.position_type else 'Sin posición'
                status = '👨‍💼 GERENTE' if member in potential_managers else '👤 Miembro'
                
                self.stdout.write(f'    {status}: {user.get_full_name()} ({user.username}) - {position_name}')
                
                # Verificar acceso actual
                from apps.communications.utils.permissions import check_lead_management_access
                has_access = check_lead_management_access(user)
                access_status = '✅ TIENE ACCESO' if has_access else '❌ SIN ACCESO'
                self.stdout.write(f'      {access_status}')
            
            # Aplicar correcciones si se especifica --fix
            if options['fix']:
                for member in potential_managers:
                    if not member.position_type or 'gerente' not in member.position_type.name.lower():
                        old_position = member.position_type.name if member.position_type else 'Sin posición'
                        member.position_type = manager_position
                        member.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'    🔧 CORREGIDO: {member.user.get_full_name()} - '
                                f'{old_position} → {manager_position.name}'
                            )
                        )
                        total_fixed += 1
        
        # Resumen final
        self.stdout.write('\n' + '=' * 60)
        if options['fix']:
            self.stdout.write(self.style.SUCCESS(f'✅ CORRECCIONES APLICADAS: {total_fixed}'))
            self.stdout.write('\n🎯 Los gerentes ahora deberían tener acceso a:')
            self.stdout.write('   - Gestión de Leads')
            self.stdout.write('   - Supervisión de Chat') 
            self.stdout.write('   - Asignación Manual de Leads')
            self.stdout.write('   - Ver miembros de su equipo')
        else:
            self.stdout.write(self.style.WARNING('ℹ️  MODO VERIFICACIÓN - No se aplicaron cambios'))
            self.stdout.write('   Para aplicar correcciones, ejecuta: python manage.py fix_manager_permissions --fix')
        
        self.stdout.write('\n🔄 Recuerda que los usuarios pueden necesitar cerrar sesión y volver a entrar')
        self.stdout.write('   para que los cambios de permisos surtan efecto completamente.\n')