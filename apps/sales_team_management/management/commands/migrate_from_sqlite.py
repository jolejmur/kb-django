# apps/sales_team_management/management/commands/migrate_from_sqlite.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.sales_team_management.models import (
    OrganizationalUnit, PositionType, TeamMembership, 
    HierarchyRelation, CommissionStructure
)
import sqlite3
import json
from datetime import datetime
from collections import defaultdict


class Command(BaseCommand):
    help = 'Migra datos desde SQLite al nuevo modelo PostgreSQL sin duplicación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sqlite-path',
            type=str,
            default='db.sqlite3',
            help='Ruta al archivo SQLite'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin hacer cambios reales'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        self.sqlite_path = options['sqlite_path']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODO SIMULACIÓN - No se harán cambios reales')
            )
        
        try:
            with transaction.atomic():
                self.migrate_data()
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

    def migrate_data(self):
        """Ejecuta todo el proceso de migración"""
        
        # 1. Conectar a SQLite
        self.stdout.write('📁 Conectando a SQLite...')
        self.sqlite_conn = sqlite3.connect(self.sqlite_path)
        self.sqlite_conn.row_factory = sqlite3.Row
        
        try:
            # 2. Migrar usuarios
            self.migrate_users()
            
            # 3. Crear tipos de posición
            self.create_position_types()
            
            # 4. Migrar equipos de venta como unidades organizacionales
            self.migrate_organizational_units()
            
            # 5. Crear estructuras de comisión por defecto
            self.create_commission_structures()
            
            # 6. Migrar membresías (CON DEDUPLICACIÓN)
            self.migrate_team_memberships()
            
            # 7. Migrar relaciones jerárquicas
            self.migrate_hierarchy_relations()
            
            # 8. Reporte final
            self.generate_migration_report()
            
        finally:
            self.sqlite_conn.close()

    def migrate_users(self):
        """Migra usuarios de SQLite a PostgreSQL"""
        self.stdout.write('👥 Migrando usuarios...')
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT id, username, email, first_name, last_name, 
                   cedula, domicilio, telefono, latitud, longitud,
                   fecha_nacimiento, is_active, is_staff, is_superuser,
                   date_joined
            FROM accounts_user
        ''')
        
        users_migrated = 0
        for row in cursor.fetchall():
            # Verificar si el usuario ya existe en PostgreSQL
            if not User.objects.filter(username=row['username']).exists():
                if not self.dry_run:
                    User.objects.create(
                        username=row['username'],
                        email=row['email'] or '',
                        first_name=row['first_name'] or '',
                        last_name=row['last_name'] or '',
                        cedula=row['cedula'],
                        domicilio=row['domicilio'] or '',
                        telefono=row['telefono'] or '',
                        latitud=row['latitud'],
                        longitud=row['longitud'],
                        fecha_nacimiento=row['fecha_nacimiento'],
                        is_active=bool(row['is_active']),
                        is_staff=bool(row['is_staff']),
                        is_superuser=bool(row['is_superuser']),
                        date_joined=row['date_joined']
                    )
                users_migrated += 1
                
        self.stdout.write(f'  ✅ {users_migrated} usuarios migrados')

    def create_position_types(self):
        """Crea los tipos de posición estándar para equipos de ventas"""
        self.stdout.write('🏷️ Creando tipos de posición...')
        
        position_types = [
            {
                'code': 'MANAGER',
                'name': 'Gerente de Equipo',
                'applicable_unit_types': 'SALES',
                'hierarchy_level': 1,
                'can_supervise': True,
                'can_have_direct_reports': True
            },
            {
                'code': 'SUPERVISOR',
                'name': 'Jefe de Venta',
                'applicable_unit_types': 'SALES',
                'hierarchy_level': 2,
                'can_supervise': True,
                'can_have_direct_reports': True
            },
            {
                'code': 'TEAM_LEAD',
                'name': 'Team Leader',
                'applicable_unit_types': 'SALES',
                'hierarchy_level': 3,
                'can_supervise': True,
                'can_have_direct_reports': True
            },
            {
                'code': 'AGENT',
                'name': 'Vendedor',
                'applicable_unit_types': 'SALES',
                'hierarchy_level': 4,
                'can_supervise': False,
                'can_have_direct_reports': False
            }
        ]
        
        created_count = 0
        for pos_type in position_types:
            if not self.dry_run:
                obj, created = PositionType.objects.get_or_create(
                    code=pos_type['code'],
                    defaults=pos_type
                )
                if created:
                    created_count += 1
            else:
                created_count += 1
                
        self.stdout.write(f'  ✅ {created_count} tipos de posición creados')

    def migrate_organizational_units(self):
        """Migra equipos de venta como unidades organizacionales"""
        self.stdout.write('🏢 Migrando unidades organizacionales...')
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute('SELECT * FROM sales_team_management_equipoventa')
        
        units_migrated = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                OrganizationalUnit.objects.get_or_create(
                    code=f'SALES_TEAM_{row["id"]}',
                    defaults={
                        'name': row['nombre'] or f'Equipo de Ventas {row["id"]}',
                        'description': row['descripcion'] or '',
                        'unit_type': 'SALES',
                        'is_active': bool(row['activo']),
                        'created_at': row['created_at']
                    }
                )
            units_migrated += 1
            
        self.stdout.write(f'  ✅ {units_migrated} unidades organizacionales migradas')

    def create_commission_structures(self):
        """Crea estructuras de comisión por defecto para cada equipo"""
        self.stdout.write('💰 Creando estructuras de comisión...')
        
        # Estructura de comisión por defecto para equipos de ventas
        default_percentages = {
            'MANAGER': 10.0,
            'SUPERVISOR': 15.0, 
            'TEAM_LEAD': 20.0,
            'AGENT': 55.0
        }
        
        if not self.dry_run:
            units = OrganizationalUnit.objects.filter(unit_type='SALES')
            for unit in units:
                CommissionStructure.objects.get_or_create(
                    organizational_unit=unit,
                    defaults={
                        'structure_name': f'Comisiones {unit.name}',
                        'commission_type': 'SALES',
                        'position_percentages': default_percentages,
                        'effective_from': timezone.now(),
                        'is_active': True
                    }
                )
        
        self.stdout.write('  ✅ Estructuras de comisión creadas')

    def migrate_team_memberships(self):
        """Migra membresías aplicando lógica de deduplicación"""
        self.stdout.write('🔗 Migrando membresías (CON DEDUPLICACIÓN)...')
        
        # Algoritmo de deduplicación:
        # 1. Para cada usuario en cada equipo, encontrar el ROL MÁS ALTO
        # 2. Crear UNA SOLA membresía con ese rol
        
        cursor = self.sqlite_conn.cursor()
        
        # Consulta unificada para obtener todos los roles de cada usuario
        # La estructura jerárquica requiere JOINs para obtener el equipo_venta_id
        cursor.execute('''
            SELECT DISTINCT
                u.id as user_id,
                u.username,
                COALESCE(
                    g.equipo_venta_id,
                    ge.equipo_venta_id,
                    ge2.equipo_venta_id,
                    ge3.equipo_venta_id
                ) as equipo_id,
                CASE 
                    WHEN g.id IS NOT NULL THEN 'MANAGER'
                    WHEN j.id IS NOT NULL THEN 'SUPERVISOR' 
                    WHEN t.id IS NOT NULL THEN 'TEAM_LEAD'
                    WHEN v.id IS NOT NULL THEN 'AGENT'
                END as role_type,
                CASE
                    WHEN g.id IS NOT NULL THEN 1
                    WHEN j.id IS NOT NULL THEN 2
                    WHEN t.id IS NOT NULL THEN 3  
                    WHEN v.id IS NOT NULL THEN 4
                END as hierarchy_level
            FROM accounts_user u
            LEFT JOIN sales_team_management_gerenteequipo g ON u.id = g.usuario_id
            LEFT JOIN sales_team_management_jefeventa j ON u.id = j.usuario_id
            LEFT JOIN sales_team_management_gerenteequipo ge ON j.gerente_equipo_id = ge.id
            LEFT JOIN sales_team_management_teamleader t ON u.id = t.usuario_id
            LEFT JOIN sales_team_management_jefeventa j2 ON t.jefe_venta_id = j2.id
            LEFT JOIN sales_team_management_gerenteequipo ge2 ON j2.gerente_equipo_id = ge2.id
            LEFT JOIN sales_team_management_vendedor v ON u.id = v.usuario_id
            LEFT JOIN sales_team_management_teamleader t2 ON v.team_leader_id = t2.id
            LEFT JOIN sales_team_management_jefeventa j3 ON t2.jefe_venta_id = j3.id
            LEFT JOIN sales_team_management_gerenteequipo ge3 ON j3.gerente_equipo_id = ge3.id
            WHERE g.id IS NOT NULL OR j.id IS NOT NULL OR t.id IS NOT NULL OR v.id IS NOT NULL
            ORDER BY u.id, hierarchy_level
        ''')
        
        # Agrupar por usuario y equipo, manteniendo solo el rol más alto
        user_roles = defaultdict(lambda: defaultdict(list))
        
        for row in cursor.fetchall():
            user_id = row['user_id']
            equipo_id = row['equipo_id']
            user_roles[user_id][equipo_id].append({
                'role_type': row['role_type'],
                'hierarchy_level': row['hierarchy_level'],
                'username': row['username']
            })
        
        memberships_created = 0
        deduplication_report = []
        
        for user_id, equipos in user_roles.items():
            for equipo_id, roles in equipos.items():
                # Encontrar el rol con el nivel jerárquico más alto (número más bajo)
                highest_role = min(roles, key=lambda x: x['hierarchy_level'])
                
                if len(roles) > 1:
                    removed_roles = [r['role_type'] for r in roles if r != highest_role]
                    deduplication_report.append({
                        'username': highest_role['username'],
                        'equipo_id': equipo_id,
                        'kept_role': highest_role['role_type'],
                        'removed_roles': removed_roles
                    })
                
                # Crear la membresía única
                if not self.dry_run:
                    try:
                        user = User.objects.get(id=user_id)
                        unit = OrganizationalUnit.objects.get(code=f'SALES_TEAM_{equipo_id}')
                        position_type = PositionType.objects.get(code=highest_role['role_type'])
                        
                        TeamMembership.objects.get_or_create(
                            user=user,
                            organizational_unit=unit,
                            position_type=position_type,
                            defaults={
                                'start_date': timezone.now(),
                                'status': 'ACTIVE',
                                'assignment_type': 'PERMANENT',
                                'is_active': True
                            }
                        )
                        memberships_created += 1
                        
                    except Exception as e:
                        self.stdout.write(f'  ⚠️ Error creando membresía para usuario {user_id}: {e}')
                else:
                    memberships_created += 1
        
        self.stdout.write(f'  ✅ {memberships_created} membresías creadas')
        
        if deduplication_report and self.verbose:
            self.stdout.write('  📋 REPORTE DE DEDUPLICACIÓN:')
            for report in deduplication_report:
                self.stdout.write(
                    f'    {report["username"]} en equipo {report["equipo_id"]}: '
                    f'mantuvo {report["kept_role"]}, removió {", ".join(report["removed_roles"])}'
                )

    def migrate_hierarchy_relations(self):
        """Migra las relaciones de supervisión directa"""
        self.stdout.write('🌳 Migrando relaciones jerárquicas...')
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT s.*, 
                   u1.username as supervisor_username,
                   u2.username as subordinado_username
            FROM sales_team_management_supervisiondirecta s
            JOIN accounts_user u1 ON s.supervisor_id = u1.id
            JOIN accounts_user u2 ON s.subordinado_id = u2.id
        ''')
        
        relations_created = 0
        for row in cursor.fetchall():
            if not self.dry_run:
                try:
                    # Encontrar las membresías correspondientes
                    supervisor_membership = TeamMembership.objects.filter(
                        user__id=row['supervisor_id'],
                        is_active=True
                    ).first()
                    
                    subordinate_membership = TeamMembership.objects.filter(
                        user__id=row['subordinado_id'],
                        is_active=True
                    ).first()
                    
                    if supervisor_membership and subordinate_membership:
                        HierarchyRelation.objects.get_or_create(
                            supervisor_membership=supervisor_membership,
                            subordinate_membership=subordinate_membership,
                            defaults={
                                'relation_type': 'DIRECT',
                                'authority_level': 'FULL',
                                'start_date': timezone.now(),
                                'justification': 'Migrado desde supervisión directa',
                                'is_primary': False,  # Supervisión directa no es primaria
                                'is_active': True
                            }
                        )
                        relations_created += 1
                    
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error creando relación: {e}')
            else:
                relations_created += 1
        
        self.stdout.write(f'  ✅ {relations_created} relaciones jerárquicas migradas')

    def generate_migration_report(self):
        """Genera reporte final de la migración"""
        self.stdout.write('📊 REPORTE DE MIGRACIÓN COMPLETADO:')
        
        if not self.dry_run:
            users_count = User.objects.count()
            units_count = OrganizationalUnit.objects.count()
            memberships_count = TeamMembership.objects.count()
            relations_count = HierarchyRelation.objects.count()
            
            self.stdout.write(f'  👥 Usuarios: {users_count}')
            self.stdout.write(f'  🏢 Unidades organizacionales: {units_count}')
            self.stdout.write(f'  🔗 Membresías (SIN DUPLICACIÓN): {memberships_count}')
            self.stdout.write(f'  🌳 Relaciones jerárquicas: {relations_count}')
        else:
            self.stdout.write('  📝 Simulación completada - Ver logs arriba para detalles')
            
        self.stdout.write(
            self.style.SUCCESS('🎉 ¡Migración completada exitosamente!')
        )