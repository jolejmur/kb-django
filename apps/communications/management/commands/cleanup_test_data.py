# apps/communications/management/commands/cleanup_test_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.sales_team_management.models import OrganizationalUnit, TeamMembership
from apps.communications.models import LeadDistributionConfig, LeadAssignment

User = get_user_model()


class Command(BaseCommand):
    help = 'Elimina datos de prueba: fuerzas de venta test/gama/beta/alpha y usuarios pepe/perez/carlos/rodrigues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se eliminaría sin hacer cambios',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar eliminación sin confirmación interactiva',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧹 Iniciando limpieza de datos de prueba...'))
        self.stdout.write('='*60)
        
        # 1. Identificar fuerzas de venta a eliminar
        self.stdout.write('\n📋 FUERZAS DE VENTA ACTUALES:')
        self.stdout.write('-'*40)
        
        all_units = OrganizationalUnit.objects.filter(unit_type='SALES')
        for unit in all_units:
            status = "✅ ACTIVA" if unit.is_active else "❌ INACTIVA"
            members_count = unit.teammembership_set.filter(is_active=True).count()
            self.stdout.write(f"  • {unit.name} ({unit.code}) - {status} - {members_count} miembros")
        
        # 2. Identificar usuarios de prueba
        self.stdout.write('\n👥 USUARIOS DE PRUEBA:')
        self.stdout.write('-'*40)
        
        test_usernames = ['pepe', 'perez', 'carlos', 'rodrigues']
        test_users = User.objects.filter(username__in=test_usernames)
        for user in test_users:
            status = "✅ ACTIVO" if user.is_active else "❌ INACTIVO"
            self.stdout.write(f"  • {user.username} ({user.get_full_name()}) - {status}")
        
        # 3. Identificar fuerzas de venta a eliminar
        self.stdout.write('\n🎯 FUERZAS DE VENTA A ELIMINAR:')
        self.stdout.write('-'*40)
        
        # Fuerzas que empiezan con 'test'
        test_units = OrganizationalUnit.objects.filter(
            unit_type='SALES',
            name__istartswith='test'
        )
        
        # Fuerzas específicas (buscar por contenido para capturar variaciones)
        specific_units = OrganizationalUnit.objects.filter(
            unit_type='SALES'
        ).filter(
            name__iregex=r'.*(alpha|beta|gamma|gama).*'
        )
        
        # Combinar todos los units a eliminar
        units_to_delete = (test_units | specific_units).distinct()
        
        if units_to_delete.exists():
            self.stdout.write("  Fuerzas de venta marcadas para eliminación:")
            for unit in units_to_delete:
                members_count = unit.teammembership_set.count()
                try:
                    lead_configs = LeadDistributionConfig.objects.filter(organizational_unit=unit).count()
                except:
                    lead_configs = 0
                try:
                    assignments = LeadAssignment.objects.filter(organizational_unit=unit).count()
                except:
                    assignments = 0
                
                self.stdout.write(f"    🗑️  {unit.name} ({unit.code})")
                self.stdout.write(f"       - {members_count} miembros")
                self.stdout.write(f"       - {lead_configs} configuraciones de leads")
                self.stdout.write(f"       - {assignments} asignaciones de leads")
        else:
            self.stdout.write("  ✅ No se encontraron fuerzas de venta de prueba para eliminar")
        
        # 4. Mostrar resumen
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📊 RESUMEN DE ELIMINACIÓN:')
        self.stdout.write('='*60)
        self.stdout.write(f"  • {test_users.count()} usuarios de prueba")
        self.stdout.write(f"  • {units_to_delete.count()} fuerzas de venta")
        
        # 5. Dry run o confirmación
        if options['dry_run']:
            self.stdout.write('\n🔍 MODO DRY-RUN: No se realizarán cambios')
            return
        
        if not test_users.exists() and not units_to_delete.exists():
            self.stdout.write('\n✅ No hay datos de prueba para eliminar')
            return
        
        # Confirmación
        if not options['force']:
            self.stdout.write('\n⚠️  Esta operación eliminará permanentemente los datos listados arriba.')
            confirm = input('❓ ¿Continuar? (escriba "si" para confirmar): ')
            if confirm.lower() != 'si':
                self.stdout.write('❌ Operación cancelada')
                return
        
        # 6. Ejecutar eliminación con transacción
        try:
            with transaction.atomic():
                deleted_counts = self._perform_cleanup(units_to_delete, test_users)
                
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('✅ LIMPIEZA COMPLETADA EXITOSAMENTE'))
                self.stdout.write('='*60)
                
                # Mostrar contadores
                self.stdout.write(f"📊 Elementos eliminados:")
                self.stdout.write(f"  • {deleted_counts['lead_configs']} configuraciones de leads")
                self.stdout.write(f"  • {deleted_counts['assignments']} asignaciones de leads")
                self.stdout.write(f"  • {deleted_counts['memberships']} membresías de equipos")
                self.stdout.write(f"  • {deleted_counts['units']} fuerzas de venta")
                self.stdout.write(f"  • {deleted_counts['users']} usuarios")
                
                # Mostrar estado final
                self.stdout.write('\n📋 FUERZAS DE VENTA ACTIVAS RESTANTES:')
                self.stdout.write('-'*50)
                remaining_units = OrganizationalUnit.objects.filter(unit_type='SALES', is_active=True)
                if remaining_units.exists():
                    for unit in remaining_units:
                        members_count = unit.teammembership_set.filter(is_active=True).count()
                        self.stdout.write(f"  ✅ {unit.name} - {members_count} miembros activos")
                else:
                    self.stdout.write("  ⚠️  No quedan fuerzas de venta activas")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante la eliminación: {str(e)}'))
            raise

    def _perform_cleanup(self, units_to_delete, test_users):
        """Realiza la limpieza y retorna contadores"""
        deleted_counts = {
            'lead_configs': 0,
            'assignments': 0, 
            'memberships': 0,
            'units': 0,
            'users': 0
        }
        
        # 1. Eliminar configuraciones de leads
        self.stdout.write('\n1️⃣ Eliminando configuraciones de leads...')
        for unit in units_to_delete:
            try:
                lead_configs = LeadDistributionConfig.objects.filter(organizational_unit=unit)
                config_count = lead_configs.count()
                if config_count > 0:
                    lead_configs.delete()
                    deleted_counts['lead_configs'] += config_count
                    self.stdout.write(f"   ✅ {config_count} configuraciones eliminadas para {unit.name}")
            except Exception as e:
                self.stdout.write(f"   ⚠️  Error con configuraciones de {unit.name}: {str(e)}")
        
        # 2. Eliminar asignaciones de leads
        self.stdout.write('\n2️⃣ Eliminando asignaciones de leads...')
        for unit in units_to_delete:
            try:
                assignments = LeadAssignment.objects.filter(organizational_unit=unit)
                assignment_count = assignments.count()
                if assignment_count > 0:
                    assignments.delete()
                    deleted_counts['assignments'] += assignment_count
                    self.stdout.write(f"   ✅ {assignment_count} asignaciones eliminadas para {unit.name}")
            except Exception as e:
                self.stdout.write(f"   ⚠️  Error con asignaciones de {unit.name}: {str(e)}")
        
        # 3. Eliminar membresías de equipos
        self.stdout.write('\n3️⃣ Eliminando membresías de equipos...')
        for unit in units_to_delete:
            memberships = TeamMembership.objects.filter(organizational_unit=unit)
            membership_count = memberships.count()
            if membership_count > 0:
                memberships.delete()
                deleted_counts['memberships'] += membership_count
                self.stdout.write(f"   ✅ {membership_count} membresías eliminadas para {unit.name}")
        
        # 4. Eliminar fuerzas de venta
        self.stdout.write('\n4️⃣ Eliminando fuerzas de venta...')
        for unit in units_to_delete:
            unit_name = unit.name
            unit.delete()
            deleted_counts['units'] += 1
            self.stdout.write(f"   ✅ Fuerza de venta '{unit_name}' eliminada")
        
        # 5. Eliminar usuarios de prueba
        self.stdout.write('\n5️⃣ Eliminando usuarios de prueba...')
        for user in test_users:
            username = user.username
            full_name = user.get_full_name()
            user.delete()
            deleted_counts['users'] += 1
            self.stdout.write(f"   ✅ Usuario '{username}' ({full_name}) eliminado")
        
        return deleted_counts