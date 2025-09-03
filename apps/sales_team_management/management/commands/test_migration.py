# apps/sales_team_management/management/commands/test_migration.py

from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from apps.sales_team_management.utils import get_commission_preview, validate_hierarchy_consistency
from apps.sales_team_management.models import OrganizationalUnit, TeamMembership, HierarchyRelation
from apps.accounts.models import User
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Prueba el nuevo sistema de jerarquías con datos migrados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-commissions',
            action='store_true',
            help='Prueba cálculos de comisiones',
        )
        parser.add_argument(
            '--test-hierarchy',
            action='store_true',
            help='Prueba consultas de jerarquía',
        )
        parser.add_argument(
            '--validate-data',
            action='store_true',
            help='Valida consistencia de datos migrados',
        )
        parser.add_argument(
            '--all-tests',
            action='store_true',
            help='Ejecuta todas las pruebas',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🧪 Iniciando pruebas del nuevo sistema de jerarquías')
        )
        
        all_tests = options['all_tests']
        
        if all_tests or options['validate_data']:
            self.test_data_validation()
        
        if all_tests or options['test_hierarchy']:
            self.test_hierarchy_queries()
        
        if all_tests or options['test_commissions']:
            self.test_commission_calculations()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Todas las pruebas completadas')
        )

    def test_data_validation(self):
        """Valida consistencia de datos migrados"""
        self.stdout.write(self.style.SUCCESS('\n📊 VALIDANDO CONSISTENCIA DE DATOS'))
        
        # 1. Verificar que no hay duplicación de roles
        self.stdout.write('Verificando duplicación de roles...')
        
        for unit in OrganizationalUnit.objects.filter(unit_type='SALES'):
            user_positions = {}
            memberships = TeamMembership.objects.filter(
                organizational_unit=unit,
                is_active=True,
                status='ACTIVE'
            )
            
            for membership in memberships:
                user_id = membership.user.id
                if user_id in user_positions:
                    self.stdout.write(
                        self.style.ERROR(
                            f'❌ DUPLICACIÓN: Usuario {membership.user.username} '
                            f'tiene múltiples roles en {unit.name}'
                        )
                    )
                else:
                    user_positions[user_id] = membership.position_type.code
            
            self.stdout.write(f'✅ {unit.name}: {len(user_positions)} usuarios únicos')
        
        # 2. Validar consistencia jerárquica
        self.stdout.write('\nValidando consistencia jerárquica...')
        
        for unit in OrganizationalUnit.objects.filter(unit_type='SALES'):
            conflicts = validate_hierarchy_consistency(unit)
            if conflicts:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {unit.name}: {len(conflicts)} conflictos encontrados')
                )
                for conflict in conflicts:
                    self.stdout.write(f'   • {conflict["description"]}')
            else:
                self.stdout.write(f'✅ {unit.name}: Jerarquía consistente')
        
        # 3. Verificar estructuras de comisiones
        self.stdout.write('\nValidando estructuras de comisiones...')
        
        for unit in OrganizationalUnit.objects.filter(unit_type='SALES'):
            commission_structures = unit.commissionstructure_set.filter(is_active=True)
            if commission_structures.exists():
                for structure in commission_structures:
                    total_percentage = sum(structure.position_percentages.values())
                    if total_percentage > 100:
                        self.stdout.write(
                            self.style.ERROR(
                                f'❌ {unit.name}: Comisiones suman {total_percentage}% (>100%)'
                            )
                        )
                    else:
                        self.stdout.write(f'✅ {unit.name}: Comisiones válidas ({total_percentage}%)')
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {unit.name}: Sin estructura de comisiones')
                )

    def test_hierarchy_queries(self):
        """Prueba consultas de jerarquía"""
        self.stdout.write(self.style.SUCCESS('\n🔍 PROBANDO CONSULTAS DE JERARQUÍA'))
        
        # Tomar algunos usuarios de ejemplo
        sample_users = User.objects.filter(
            team_memberships__is_active=True,
            team_memberships__status='ACTIVE'
        ).distinct()[:5]
        
        for user in sample_users:
            self.stdout.write(f'\n👤 Usuario: {user.get_full_name() or user.username}')
            
            # Obtener todas las membresías del usuario
            memberships = user.team_memberships.filter(
                is_active=True,
                status='ACTIVE'
            )
            
            for membership in memberships:
                self.stdout.write(
                    f'  📋 {membership.organizational_unit.name}: '
                    f'{membership.position_type.name}'
                )
                
                # Supervisores
                supervisors = membership.subordinate_relations.all()
                if supervisors:
                    self.stdout.write('    👆 Supervisores:')
                    for supervisor_rel in supervisors:
                        self.stdout.write(
                            f'      • {supervisor_rel.supervisor_membership.user.get_full_name()} '
                            f'({supervisor_rel.get_relation_type_display()})'
                        )
                
                # Subordinados
                subordinates = membership.supervisor_relations.all()
                if subordinates:
                    self.stdout.write('    👇 Subordinados:')
                    for subordinate_rel in subordinates:
                        self.stdout.write(
                            f'      • {subordinate_rel.subordinate_membership.user.get_full_name()} '
                            f'({subordinate_rel.get_relation_type_display()})'
                        )

    def test_commission_calculations(self):
        """Prueba cálculos de comisiones"""
        self.stdout.write(self.style.SUCCESS('\n💰 PROBANDO CÁLCULOS DE COMISIONES'))
        
        # Obtener algunos usuarios de ventas para probar
        sales_memberships = TeamMembership.objects.filter(
            organizational_unit__unit_type='SALES',
            is_active=True,
            status='ACTIVE'
        ).select_related('user', 'position_type', 'organizational_unit')[:10]
        
        test_sale_amount = Decimal('100000.00')  # $100K de venta
        
        self.stdout.write(f'Simulando ventas de ${test_sale_amount:,}')
        
        for membership in sales_memberships:
            self.stdout.write(
                f'\n🛒 Venta por: {membership.user.get_full_name() or membership.user.username} '
                f'({membership.position_type.name}) en {membership.organizational_unit.name}'
            )
            
            try:
                commission_distribution = get_commission_preview(test_sale_amount, membership)
                
                if 'error' in commission_distribution:
                    self.stdout.write(
                        self.style.ERROR(f'   ❌ Error: {commission_distribution["error"]}')
                    )
                    continue
                
                total_distributed = Decimal('0')
                
                for user_id, distribution in commission_distribution.items():
                    user_name = distribution['user'].get_full_name() or distribution['user'].username
                    percentage = distribution['percentage']
                    amount = distribution['amount']
                    reason = distribution['reason']
                    
                    total_distributed += amount
                    
                    self.stdout.write(
                        f'   💵 {user_name}: {percentage}% = ${amount:,.2f} ({reason})'
                    )
                
                self.stdout.write(f'   📊 Total distribuido: ${total_distributed:,.2f}')
                
                # Verificar que no exceda 100%
                total_percentage = sum(d['percentage'] for d in commission_distribution.values())
                if total_percentage > 100:
                    self.stdout.write(
                        self.style.ERROR(f'   ❌ PROBLEMA: Total {total_percentage}% excede 100%')
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Error calculando comisiones: {str(e)}')
                )
        
        # Probar casos específicos de supervisión directa
        self.stdout.write(self.style.SUCCESS('\n🎯 PROBANDO SUPERVISIÓN DIRECTA'))
        
        direct_relations = HierarchyRelation.objects.filter(
            relation_type='DIRECT',
            is_active=True
        ).select_related(
            'supervisor_membership__user',
            'subordinate_membership__user',
            'subordinate_membership__position_type'
        )[:5]
        
        for relation in direct_relations:
            subordinate_membership = relation.subordinate_membership
            
            self.stdout.write(
                f'\n🎯 Supervisión directa: '
                f'{relation.supervisor_membership.user.get_full_name()} → '
                f'{subordinate_membership.user.get_full_name()}'
            )
            
            try:
                commission_distribution = get_commission_preview(test_sale_amount, subordinate_membership)
                
                if 'error' not in commission_distribution:
                    supervisor_dist = commission_distribution.get(relation.supervisor_membership.user.id)
                    if supervisor_dist:
                        self.stdout.write(
                            f'   💵 Supervisor recibe: {supervisor_dist["percentage"]}% '
                            f'= ${supervisor_dist["amount"]:,.2f} '
                            f'({supervisor_dist["reason"]})'
                        )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ Error: {str(e)}')
                )

    def show_database_stats(self):
        """Muestra estadísticas de la base de datos"""
        self.stdout.write(self.style.SUCCESS('\n📈 ESTADÍSTICAS DE LA BASE DE DATOS'))
        
        with connection.cursor() as cursor:
            # Contar registros en nuevas tablas
            new_tables = [
                'sales_team_management_organizationalunit',
                'sales_team_management_positiontype', 
                'sales_team_management_teammembership',
                'sales_team_management_hierarchyrelation',
                'sales_team_management_commissionstructure'
            ]
            
            for table in new_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.stdout.write(f'  {table}: {count} registros')
                except Exception as e:
                    self.stdout.write(f'  {table}: Error - {str(e)}')
            
            # Contar registros en tablas antiguas
            old_tables = [
                'sales_team_management_equipoventa',
                'sales_team_management_gerenteequipo',
                'sales_team_management_jefeventa', 
                'sales_team_management_teamleader',
                'sales_team_management_vendedor',
                'sales_team_management_supervisiondirecta'
            ]
            
            self.stdout.write('\n📊 Tablas antiguas (para comparación):')
            for table in old_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.stdout.write(f'  {table}: {count} registros')
                except Exception as e:
                    self.stdout.write(f'  {table}: Error - {str(e)}')