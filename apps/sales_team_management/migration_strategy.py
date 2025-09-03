# apps/sales_team_management/migrations/migration_strategy.py
# ESTRATEGIA DE MIGRACIÓN PARA EVITAR DUPLICACIÓN DE ROLES

"""
PROBLEMA ACTUAL:
- Un gerente aparece como GerenteEquipo, JefeVenta y TeamLeader debido a supervisión directa
- Necesitamos identificar el ROL REAL del usuario y crear solo UNA membresía

ESTRATEGIA:
1. Identificar el rol jerárquico MÁS ALTO de cada usuario en cada equipo
2. Crear UNA SOLA TeamMembership con el rol más alto
3. Crear HierarchyRelation para supervisión directa donde corresponda
"""

from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.sales_team_management.models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor, SupervisionDirecta
)
from apps.sales_team_management.models import (
    OrganizationalUnit, PositionType, TeamMembership, HierarchyRelation, CommissionStructure
)


class SalesTeamMigrator:
    """
    Migrador inteligente que evita duplicación de roles
    """
    
    def __init__(self):
        self.position_hierarchy = {
            'MANAGER': 1,      # Gerente (más alto)
            'SUPERVISOR': 2,   # Jefe de Venta  
            'TEAM_LEAD': 3,    # Team Leader
            'AGENT': 4         # Vendedor (más bajo)
        }
        
        self.migration_log = []
    
    def log(self, message):
        """Registra eventos de migración"""
        print(f"[MIGRATION] {message}")
        self.migration_log.append(f"{timezone.now()}: {message}")
    
    @transaction.atomic
    def migrate_all(self):
        """Ejecuta migración completa"""
        self.log("Iniciando migración de estructura de equipos de ventas")
        
        # Paso 1: Crear tipos de posiciones base
        self.create_position_types()
        
        # Paso 2: Migrar equipos de venta a unidades organizacionales
        self.migrate_sales_teams()
        
        # Paso 3: Analizar y crear membresías sin duplicación
        self.migrate_team_memberships()
        
        # Paso 4: Crear relaciones jerárquicas
        self.create_hierarchy_relations()
        
        # Paso 5: Migrar estructuras de comisiones
        self.migrate_commission_structures()
        
        self.log("Migración completada exitosamente")
        return self.migration_log
    
    def create_position_types(self):
        """Crea los tipos de posiciones base para ventas"""
        self.log("Creando tipos de posiciones base")
        
        positions = [
            {
                'code': 'MANAGER',
                'name': 'Gerente de Equipo',
                'applicable_unit_types': 'SALES',
                'hierarchy_level': 1,
                'can_supervise': True,
                'can_have_direct_reports': True,
            },
            {
                'code': 'SUPERVISOR', 
                'name': 'Jefe de Venta',
                'applicable_unit_types': 'SALES',
                'hierarchy_level': 2,
                'can_supervise': True,
                'can_have_direct_reports': True,
            },
            {
                'code': 'TEAM_LEAD',
                'name': 'Team Leader', 
                'applicable_unit_types': 'SALES',
                'hierarchy_level': 3,
                'can_supervise': True,
                'can_have_direct_reports': False,
            },
            {
                'code': 'AGENT',
                'name': 'Vendedor',
                'applicable_unit_types': 'SALES', 
                'hierarchy_level': 4,
                'can_supervise': False,
                'can_have_direct_reports': False,
            }
        ]
        
        for pos_data in positions:
            position, created = PositionType.objects.get_or_create(
                code=pos_data['code'],
                defaults=pos_data
            )
            if created:
                self.log(f"Creado tipo de posición: {position.name}")
    
    def migrate_sales_teams(self):
        """Migra EquipoVenta a OrganizationalUnit"""
        self.log("Migrando equipos de venta a unidades organizacionales")
        
        for equipo in EquipoVenta.objects.filter(activo=True):
            unit, created = OrganizationalUnit.objects.get_or_create(
                code=f"VTA_{equipo.nombre.upper().replace(' ', '_')}",
                defaults={
                    'name': equipo.nombre,
                    'description': equipo.descripcion,
                    'unit_type': 'SALES',
                    'is_active': equipo.activo,
                }
            )
            if created:
                self.log(f"Creada unidad organizacional: {unit.name}")
    
    def migrate_team_memberships(self):
        """
        Migra usuarios a membresías identificando el rol MÁS ALTO por equipo
        EVITA DUPLICACIÓN
        """
        self.log("Analizando roles de usuarios para evitar duplicación")
        
        # Obtener todos los usuarios que tienen roles en equipos de ventas
        users_in_sales = set()
        
        # Recopilar usuarios de todas las tablas
        for gerente in GerenteEquipo.objects.filter(activo=True):
            users_in_sales.add((gerente.usuario, gerente.equipo_venta))
        
        for jefe in JefeVenta.objects.filter(activo=True):
            users_in_sales.add((jefe.usuario, jefe.gerente_equipo.equipo_venta))
        
        for tl in TeamLeader.objects.filter(activo=True):
            users_in_sales.add((tl.usuario, tl.jefe_venta.gerente_equipo.equipo_venta))
        
        for vendedor in Vendedor.objects.filter(activo=True):
            users_in_sales.add((vendedor.usuario, vendedor.team_leader.jefe_venta.gerente_equipo.equipo_venta))
        
        # Analizar cada usuario-equipo para determinar su ROL REAL
        for user, old_equipo in users_in_sales:
            self.migrate_user_membership(user, old_equipo)
    
    def migrate_user_membership(self, user, old_equipo):
        """
        Determina el rol REAL de un usuario en un equipo (sin duplicación)
        """
        # Obtener la nueva unidad organizacional
        try:
            unit = OrganizationalUnit.objects.get(
                code=f"VTA_{old_equipo.nombre.upper().replace(' ', '_')}"
            )
        except OrganizationalUnit.DoesNotExist:
            self.log(f"ERROR: No se encontró unidad para equipo {old_equipo.nombre}")
            return
        
        # Determinar el rol MÁS ALTO del usuario en este equipo
        user_roles = self.analyze_user_roles_in_team(user, old_equipo)
        
        if not user_roles:
            self.log(f"WARNING: Usuario {user.username} no tiene roles activos en {old_equipo.nombre}")
            return
        
        # Tomar el rol de nivel MÁS ALTO (número menor)
        highest_role = min(user_roles, key=lambda x: self.position_hierarchy[x])
        
        self.log(f"Usuario {user.username} en {old_equipo.nombre}: ROL REAL = {highest_role}")
        
        # Crear la membresía única
        position_type = PositionType.objects.get(code=highest_role)
        
        membership, created = TeamMembership.objects.get_or_create(
            user=user,
            organizational_unit=unit,
            position_type=position_type,
            defaults={
                'start_date': timezone.now(),
                'status': 'ACTIVE',
                'assignment_type': 'PERMANENT',
                'notes': f'Migrado desde sistema anterior. Roles detectados: {", ".join(user_roles)}',
                'is_active': True,
            }
        )
        
        if created:
            self.log(f"✓ Creada membresía: {user.username} como {highest_role} en {unit.name}")
        else:
            self.log(f"⚠ Membresía ya existe: {user.username} en {unit.name}")
    
    def analyze_user_roles_in_team(self, user, equipo):
        """
        Analiza todos los roles que tiene un usuario en un equipo
        Retorna lista de códigos de posición
        """
        roles_found = []
        
        # Verificar si es gerente
        if GerenteEquipo.objects.filter(
            usuario=user, 
            equipo_venta=equipo, 
            activo=True
        ).exists():
            roles_found.append('MANAGER')
        
        # Verificar si es jefe de venta
        if JefeVenta.objects.filter(
            usuario=user,
            gerente_equipo__equipo_venta=equipo,
            activo=True
        ).exists():
            roles_found.append('SUPERVISOR')
        
        # Verificar si es team leader
        if TeamLeader.objects.filter(
            usuario=user,
            jefe_venta__gerente_equipo__equipo_venta=equipo,
            activo=True
        ).exists():
            roles_found.append('TEAM_LEAD')
        
        # Verificar si es vendedor
        if Vendedor.objects.filter(
            usuario=user,
            team_leader__jefe_venta__gerente_equipo__equipo_venta=equipo,
            activo=True
        ).exists():
            roles_found.append('AGENT')
        
        return roles_found
    
    def create_hierarchy_relations(self):
        """
        Crea relaciones jerárquicas normales y de supervisión directa
        """
        self.log("Creando relaciones jerárquicas")
        
        # 1. Crear relaciones normales basadas en la jerarquía estándar
        self.create_normal_hierarchy_relations()
        
        # 2. Crear relaciones de supervisión directa
        self.create_direct_supervision_relations()
    
    def create_normal_hierarchy_relations(self):
        """Crea relaciones jerárquicas normales"""
        self.log("Creando relaciones jerárquicas normales")
        
        # Para cada unidad organizacional de ventas
        for unit in OrganizationalUnit.objects.filter(unit_type='SALES'):
            
            # Obtener membresías por nivel jerárquico
            managers = unit.team_memberships.filter(
                position_type__code='MANAGER',
                is_active=True,
                status='ACTIVE'
            )
            supervisors = unit.team_memberships.filter(
                position_type__code='SUPERVISOR', 
                is_active=True,
                status='ACTIVE'
            )
            team_leads = unit.team_memberships.filter(
                position_type__code='TEAM_LEAD',
                is_active=True, 
                status='ACTIVE'
            )
            agents = unit.team_memberships.filter(
                position_type__code='AGENT',
                is_active=True,
                status='ACTIVE'
            )
            
            # Crear relaciones: Manager → Supervisor
            for manager in managers:
                for supervisor in supervisors:
                    # Verificar si esta relación existía en el modelo anterior
                    if self.should_create_manager_supervisor_relation(manager.user, supervisor.user, unit):
                        HierarchyRelation.objects.get_or_create(
                            supervisor_membership=manager,
                            subordinate_membership=supervisor,
                            defaults={
                                'relation_type': 'NORMAL',
                                'authority_level': 'FULL',
                                'is_primary': True,
                                'justification': 'Relación jerárquica normal migrada'
                            }
                        )
                        self.log(f"Relación: {manager.user.username} → {supervisor.user.username}")
            
            # Crear relaciones: Supervisor → Team Lead
            for supervisor in supervisors:
                for team_lead in team_leads:
                    if self.should_create_supervisor_teamlead_relation(supervisor.user, team_lead.user, unit):
                        HierarchyRelation.objects.get_or_create(
                            supervisor_membership=supervisor,
                            subordinate_membership=team_lead,
                            defaults={
                                'relation_type': 'NORMAL',
                                'authority_level': 'FULL', 
                                'is_primary': True,
                                'justification': 'Relación jerárquica normal migrada'
                            }
                        )
                        self.log(f"Relación: {supervisor.user.username} → {team_lead.user.username}")
            
            # Crear relaciones: Team Lead → Agent
            for team_lead in team_leads:
                for agent in agents:
                    if self.should_create_teamlead_agent_relation(team_lead.user, agent.user, unit):
                        HierarchyRelation.objects.get_or_create(
                            supervisor_membership=team_lead,
                            subordinate_membership=agent,
                            defaults={
                                'relation_type': 'NORMAL',
                                'authority_level': 'FULL',
                                'is_primary': True, 
                                'justification': 'Relación jerárquica normal migrada'
                            }
                        )
                        self.log(f"Relación: {team_lead.user.username} → {agent.user.username}")
    
    def create_direct_supervision_relations(self):
        """Migra supervisiones directas del modelo anterior"""
        self.log("Migrando supervisiones directas")
        
        for supervision in SupervisionDirecta.objects.filter(activo=True):
            # Obtener membresías correspondientes
            try:
                unit = OrganizationalUnit.objects.get(
                    code=f"VTA_{supervision.equipo_venta.nombre.upper().replace(' ', '_')}"
                )
                
                supervisor_membership = TeamMembership.objects.get(
                    user=supervision.supervisor,
                    organizational_unit=unit,
                    is_active=True
                )
                
                subordinate_membership = TeamMembership.objects.get(
                    user=supervision.subordinado,
                    organizational_unit=unit,
                    is_active=True
                )
                
                # Crear relación de supervisión directa
                relation, created = HierarchyRelation.objects.get_or_create(
                    supervisor_membership=supervisor_membership,
                    subordinate_membership=subordinate_membership,
                    defaults={
                        'relation_type': 'DIRECT',
                        'authority_level': 'FULL',
                        'is_primary': False,  # No es la línea principal
                        'justification': f'Supervisión directa migrada: {supervision.notas}',
                        'start_date': supervision.fecha_inicio,
                    }
                )
                
                if created:
                    self.log(f"✓ Supervisión directa: {supervision.supervisor.username} → {supervision.subordinado.username}")
                
            except (OrganizationalUnit.DoesNotExist, TeamMembership.DoesNotExist) as e:
                self.log(f"ERROR migrando supervisión directa: {e}")
    
    def should_create_manager_supervisor_relation(self, manager_user, supervisor_user, unit):
        """Verifica si debe crear relación manager-supervisor basada en datos originales"""
        # Lógica para determinar si esta relación existía en el modelo original
        # Por ahora, crear relación si ambos existen en el equipo
        return True
    
    def should_create_supervisor_teamlead_relation(self, supervisor_user, teamlead_user, unit):
        """Verifica si debe crear relación supervisor-teamlead basada en datos originales"""
        # Verificar en el modelo original si este team leader reportaba a este supervisor
        old_equipo_name = unit.name
        try:
            old_equipo = EquipoVenta.objects.get(nombre=old_equipo_name)
            
            # Buscar si existe la relación en el modelo anterior
            team_leader_obj = TeamLeader.objects.filter(
                usuario=teamlead_user,
                jefe_venta__usuario=supervisor_user,
                jefe_venta__gerente_equipo__equipo_venta=old_equipo,
                activo=True
            ).first()
            
            return team_leader_obj is not None
        except:
            return True  # Si no se puede verificar, crear la relación
    
    def should_create_teamlead_agent_relation(self, teamlead_user, agent_user, unit):
        """Verifica si debe crear relación teamlead-agent basada en datos originales"""
        old_equipo_name = unit.name
        try:
            old_equipo = EquipoVenta.objects.get(nombre=old_equipo_name)
            
            # Buscar si existe la relación en el modelo anterior
            vendedor_obj = Vendedor.objects.filter(
                usuario=agent_user,
                team_leader__usuario=teamlead_user,
                team_leader__jefe_venta__gerente_equipo__equipo_venta=old_equipo,
                activo=True
            ).first()
            
            return vendedor_obj is not None
        except:
            return True
    
    def migrate_commission_structures(self):
        """Migra estructuras de comisiones"""
        self.log("Migrando estructuras de comisiones")
        
        from apps.sales_team_management.models import ComisionVenta
        
        for comision in ComisionVenta.objects.filter(activo=True):
            unit = OrganizationalUnit.objects.get(
                code=f"VTA_{comision.equipo_venta.nombre.upper().replace(' ', '_')}"
            )
            
            position_percentages = {
                'MANAGER': float(comision.porcentaje_gerente_equipo),
                'SUPERVISOR': float(comision.porcentaje_jefe_venta), 
                'TEAM_LEAD': float(comision.porcentaje_team_leader),
                'AGENT': float(comision.porcentaje_vendedor),
            }
            
            CommissionStructure.objects.get_or_create(
                organizational_unit=unit,
                structure_name=f"Comisiones {unit.name}",
                defaults={
                    'commission_type': 'SALES',
                    'position_percentages': position_percentages,
                    'effective_from': comision.created_at,
                    'is_active': True,
                }
            )
            
            self.log(f"✓ Migrada estructura de comisiones para {unit.name}")


# Función principal para ejecutar la migración
def run_migration():
    """
    Función principal para ejecutar la migración
    """
    migrator = SalesTeamMigrator()
    return migrator.migrate_all()


if __name__ == "__main__":
    # Para testing
    log = run_migration()
    print("\n".join(log))