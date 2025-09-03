# apps/sales_team_management/management/commands/migrate_legacy_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.sales_team_management.models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor, SupervisionDirecta
)
import sqlite3
from datetime import datetime


class Command(BaseCommand):
    help = 'Migra datos del modelo antiguo desde SQLite para mantener compatibilidad'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sqlite-path',
            type=str,
            default='db_backup_20250730_105549/db.sqlite3',
            help='Ruta al archivo SQLite'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin hacer cambios reales'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.sqlite_path = options['sqlite_path']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODO SIMULACIÓN - No se harán cambios reales')
            )
        
        try:
            with transaction.atomic():
                self.migrate_legacy_data()
                if self.dry_run:
                    raise Exception("Rollback intencional para dry-run")
                    
        except Exception as e:
            if "Rollback intencional" in str(e):
                self.stdout.write(
                    self.style.SUCCESS('✅ Simulación completada exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error durante migración: {e}')
                )
                raise

    def migrate_legacy_data(self):
        """Migra datos del modelo antiguo desde SQLite"""
        
        # Conectar a SQLite
        self.stdout.write('📁 Conectando a SQLite...')
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        
        try:
            # 1. Migrar equipos de venta
            self.migrate_equipos_venta(sqlite_conn)
            
            # 2. Migrar gerentes
            self.migrate_gerentes_equipo(sqlite_conn)
            
            # 3. Migrar jefes de venta
            self.migrate_jefes_venta(sqlite_conn)
            
            # 4. Migrar team leaders
            self.migrate_team_leaders(sqlite_conn)
            
            # 5. Migrar vendedores
            self.migrate_vendedores(sqlite_conn)
            
            # 6. Migrar supervisión directa
            self.migrate_supervision_directa(sqlite_conn)
            
            # 7. Reporte final
            self.generate_report()
            
        finally:
            sqlite_conn.close()

    def migrate_equipos_venta(self, sqlite_conn):
        """Migra equipos de venta"""
        self.stdout.write('🏢 Migrando equipos de venta...')
        
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT * FROM sales_team_management_equipoventa')
        
        equipos_migrated = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                EquipoVenta.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        'nombre': row['nombre'],
                        'descripcion': row['descripcion'] or '',
                        'activo': bool(row['activo']),
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
                )
            equipos_migrated += 1
            
        self.stdout.write(f'  ✅ {equipos_migrated} equipos de venta migrados')

    def migrate_gerentes_equipo(self, sqlite_conn):
        """Migra gerentes de equipo"""
        self.stdout.write('👨‍💼 Migrando gerentes de equipo...')
        
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT * FROM sales_team_management_gerenteequipo')
        
        gerentes_migrated = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                try:
                    user = User.objects.get(id=row['usuario_id'])
                    equipo = EquipoVenta.objects.get(id=row['equipo_venta_id'])
                    
                    GerenteEquipo.objects.get_or_create(
                        id=row['id'],
                        defaults={
                            'usuario': user,
                            'equipo_venta': equipo,
                            'activo': bool(row['activo']),
                            'created_at': row['created_at']
                        }
                    )
                    gerentes_migrated += 1
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error migrando gerente ID {row["id"]}: {e}')
            else:
                gerentes_migrated += 1
                
        self.stdout.write(f'  ✅ {gerentes_migrated} gerentes migrados')

    def migrate_jefes_venta(self, sqlite_conn):
        """Migra jefes de venta"""
        self.stdout.write('👨‍💻 Migrando jefes de venta...')
        
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT * FROM sales_team_management_jefeventa')
        
        jefes_migrated = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                try:
                    user = User.objects.get(id=row['usuario_id'])
                    gerente = GerenteEquipo.objects.get(id=row['gerente_equipo_id'])
                    
                    JefeVenta.objects.get_or_create(
                        id=row['id'],
                        defaults={
                            'usuario': user,
                            'gerente_equipo': gerente,
                            'activo': bool(row['activo']),
                            'created_at': row['created_at']
                        }
                    )
                    jefes_migrated += 1
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error migrando jefe ID {row["id"]}: {e}')
            else:
                jefes_migrated += 1
                
        self.stdout.write(f'  ✅ {jefes_migrated} jefes de venta migrados')

    def migrate_team_leaders(self, sqlite_conn):
        """Migra team leaders"""
        self.stdout.write('👥 Migrando team leaders...')
        
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT * FROM sales_team_management_teamleader')
        
        leaders_migrated = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                try:
                    user = User.objects.get(id=row['usuario_id'])
                    jefe = JefeVenta.objects.get(id=row['jefe_venta_id'])
                    
                    TeamLeader.objects.get_or_create(
                        id=row['id'],
                        defaults={
                            'usuario': user,
                            'jefe_venta': jefe,
                            'activo': bool(row['activo']),
                            'created_at': row['created_at']
                        }
                    )
                    leaders_migrated += 1
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error migrando team leader ID {row["id"]}: {e}')
            else:
                leaders_migrated += 1
                
        self.stdout.write(f'  ✅ {leaders_migrated} team leaders migrados')

    def migrate_vendedores(self, sqlite_conn):
        """Migra vendedores"""
        self.stdout.write('🏪 Migrando vendedores...')
        
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT * FROM sales_team_management_vendedor')
        
        vendedores_migrated = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                try:
                    user = User.objects.get(id=row['usuario_id'])
                    team_leader = TeamLeader.objects.get(id=row['team_leader_id'])
                    
                    Vendedor.objects.get_or_create(
                        id=row['id'],
                        defaults={
                            'usuario': user,
                            'team_leader': team_leader,
                            'activo': bool(row['activo']),
                            'created_at': row['created_at']
                        }
                    )
                    vendedores_migrated += 1
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error migrando vendedor ID {row["id"]}: {e}')
            else:
                vendedores_migrated += 1
                
        self.stdout.write(f'  ✅ {vendedores_migrated} vendedores migrados')

    def migrate_supervision_directa(self, sqlite_conn):
        """Migra supervisión directa"""
        self.stdout.write('🎯 Migrando supervisión directa...')
        
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT * FROM sales_team_management_supervisiondirecta')
        
        supervision_migrated = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                try:
                    supervisor = User.objects.get(id=row['supervisor_id'])
                    subordinado = User.objects.get(id=row['subordinado_id'])
                    equipo = EquipoVenta.objects.get(id=row['equipo_venta_id'])
                    
                    SupervisionDirecta.objects.get_or_create(
                        id=row['id'],
                        defaults={
                            'supervisor': supervisor,
                            'subordinado': subordinado,
                            'equipo_venta': equipo,
                            'tipo_supervision': row['tipo_supervision'],
                            'activo': bool(row['activo']),
                            'fecha_inicio': row['fecha_inicio'],
                            'fecha_fin': row['fecha_fin'],
                            'notas': row['notas'] or ''
                        }
                    )
                    supervision_migrated += 1
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error migrando supervisión ID {row["id"]}: {e}')
            else:
                supervision_migrated += 1
                
        self.stdout.write(f'  ✅ {supervision_migrated} supervisiones directas migradas')

    def generate_report(self):
        """Genera reporte final"""
        self.stdout.write('📊 REPORTE DE MIGRACIÓN DE DATOS LEGACY:')
        
        if not self.dry_run:
            equipos = EquipoVenta.objects.count()
            gerentes = GerenteEquipo.objects.count()
            jefes = JefeVenta.objects.count()
            leaders = TeamLeader.objects.count()
            vendedores = Vendedor.objects.count()
            supervision = SupervisionDirecta.objects.count()
            
            self.stdout.write(f'  🏢 Equipos de venta: {equipos}')
            self.stdout.write(f'  👨‍💼 Gerentes: {gerentes}')
            self.stdout.write(f'  👨‍💻 Jefes de venta: {jefes}')
            self.stdout.write(f'  👥 Team leaders: {leaders}')
            self.stdout.write(f'  🏪 Vendedores: {vendedores}')
            self.stdout.write(f'  🎯 Supervisiones directas: {supervision}')
        else:
            self.stdout.write('  📝 Simulación completada - Ver logs arriba para detalles')
            
        self.stdout.write(
            self.style.SUCCESS('🎉 ¡Migración de datos legacy completada!')
        )