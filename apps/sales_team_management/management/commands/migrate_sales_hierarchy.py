# apps/sales_team_management/management/commands/migrate_sales_hierarchy.py

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.sales_team_management.migration_strategy import SalesTeamMigrator
import json


class Command(BaseCommand):
    help = 'Migra la estructura jerárquica de ventas al nuevo modelo sin duplicación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta la migración en modo simulación (no hace cambios)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Muestra información detallada del proceso',
        )
        parser.add_argument(
            '--backup-log',
            type=str,
            help='Archivo donde guardar el log de migración',
            default=f'migration_log_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        backup_log = options['backup_log']
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando migración de estructura jerárquica de ventas')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  MODO SIMULACIÓN - No se harán cambios permanentes')
            )
        
        try:
            if dry_run:
                # En modo dry-run, usar transacción que se revierte
                with transaction.atomic():
                    migrator = SalesTeamMigrator()
                    migration_log = migrator.migrate_all()
                    
                    # Forzar rollback en dry-run
                    raise transaction.TransactionManagementError("Dry run - rolling back")
            else:
                # Migración real
                migrator = SalesTeamMigrator()
                migration_log = migrator.migrate_all()
            
        except transaction.TransactionManagementError as e:
            if "Dry run" in str(e):
                self.stdout.write(
                    self.style.SUCCESS('✅ Simulación completada exitosamente')
                )
                migration_log = migrator.migration_log
            else:
                raise
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error durante la migración: {str(e)}')
            )
            raise
        
        # Mostrar resumen
        self.show_migration_summary(migration_log, verbose)
        
        # Guardar log
        self.save_migration_log(migration_log, backup_log)
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('🎉 Migración completada exitosamente')
            )
            self.stdout.write(
                self.style.WARNING('⚠️  Recuerda actualizar tu código para usar los nuevos modelos')
            )

    def show_migration_summary(self, migration_log, verbose):
        """Muestra resumen de la migración"""
        self.stdout.write(self.style.SUCCESS('\n📊 RESUMEN DE MIGRACIÓN:'))
        
        # Contar eventos por tipo
        created_units = len([log for log in migration_log if 'Creada unidad organizacional' in log])
        created_positions = len([log for log in migration_log if 'Creado tipo de posición' in log])
        created_memberships = len([log for log in migration_log if '✓ Creada membresía' in log])
        created_relations = len([log for log in migration_log if 'Relación:' in log])
        created_direct = len([log for log in migration_log if '✓ Supervisión directa' in log])
        created_commissions = len([log for log in migration_log if '✓ Migrada estructura de comisiones' in log])
        
        self.stdout.write(f'  • Unidades organizacionales creadas: {created_units}')
        self.stdout.write(f'  • Tipos de posiciones creados: {created_positions}')
        self.stdout.write(f'  • Membresías de equipo creadas: {created_memberships}')
        self.stdout.write(f'  • Relaciones jerárquicas normales: {created_relations}')
        self.stdout.write(f'  • Relaciones de supervisión directa: {created_direct}')
        self.stdout.write(f'  • Estructuras de comisiones migradas: {created_commissions}')
        
        # Mostrar warnings y errores
        warnings = [log for log in migration_log if 'WARNING' in log]
        errors = [log for log in migration_log if 'ERROR' in log]
        
        if warnings:
            self.stdout.write(self.style.WARNING(f'\n⚠️  {len(warnings)} advertencias encontradas:'))
            for warning in warnings:
                self.stdout.write(f'  • {warning}')
        
        if errors:
            self.stdout.write(self.style.ERROR(f'\n❌ {len(errors)} errores encontrados:'))
            for error in errors:
                self.stdout.write(f'  • {error}')
        
        if verbose:
            self.stdout.write(self.style.SUCCESS('\n📝 LOG DETALLADO:'))
            for log_entry in migration_log:
                self.stdout.write(f'  {log_entry}')

    def save_migration_log(self, migration_log, filename):
        """Guarda el log de migración en archivo JSON"""
        log_data = {
            'migration_date': timezone.now().isoformat(),
            'total_entries': len(migration_log),
            'log_entries': migration_log,
            'summary': {
                'units_created': len([log for log in migration_log if 'Creada unidad organizacional' in log]),
                'positions_created': len([log for log in migration_log if 'Creado tipo de posición' in log]),
                'memberships_created': len([log for log in migration_log if '✓ Creada membresía' in log]),
                'relations_created': len([log for log in migration_log if 'Relación:' in log]),
                'direct_supervisions': len([log for log in migration_log if '✓ Supervisión directa' in log]),
                'commissions_migrated': len([log for log in migration_log if '✓ Migrada estructura de comisiones' in log]),
                'warnings': len([log for log in migration_log if 'WARNING' in log]),
                'errors': len([log for log in migration_log if 'ERROR' in log]),
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(f'📋 Log de migración guardado en: {filename}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error guardando log: {str(e)}')
            )