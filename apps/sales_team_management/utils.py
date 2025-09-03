# apps/sales_team_management/utils.py
# UTILIDADES PARA CÁLCULO DE COMISIONES Y JERARQUÍAS

from decimal import Decimal
from typing import Dict, List, Tuple
from django.db.models import Q
from .models import TeamMembership, HierarchyRelation, CommissionStructure, PositionType


class CommissionCalculator:
    """
    Calculadora de comisiones que maneja la lógica compleja de distribución
    según quién hace la venta y la estructura jerárquica
    """
    
    def __init__(self, commission_structure: CommissionStructure):
        self.commission_structure = commission_structure
        self.position_hierarchy = self._build_position_hierarchy()
    
    def _build_position_hierarchy(self) -> Dict[str, int]:
        """Construye diccionario de jerarquía de posiciones"""
        positions = PositionType.objects.filter(
            applicable_unit_types__contains=self.commission_structure.organizational_unit.unit_type
        ).order_by('hierarchy_level')
        
        return {pos.code: pos.hierarchy_level for pos in positions}
    
    def calculate_distribution(self, sale_amount: Decimal, seller_membership: TeamMembership) -> Dict:
        """
        Calcula distribución de comisiones para una venta
        
        Args:
            sale_amount: Monto de la venta
            seller_membership: Membresía del usuario que hizo la venta
            
        Returns:
            Dict con distribución de comisiones por usuario
        """
        distribution = {}
        
        # 1. El vendedor recibe comisiones de su nivel hacia abajo
        seller_commission = self._calculate_seller_commission(seller_membership)
        
        distribution[seller_membership.user.id] = {
            'user': seller_membership.user,
            'membership': seller_membership,
            'positions_covered': self._get_positions_at_or_below(seller_membership.position_type.hierarchy_level),
            'percentage': seller_commission,
            'amount': sale_amount * (seller_commission / 100),
            'reason': f'Venta realizada como {seller_membership.position_type.name}'
        }
        
        # 2. Supervisores reciben sus comisiones correspondientes
        supervisor_distributions = self._calculate_supervisor_commissions(seller_membership, sale_amount)
        distribution.update(supervisor_distributions)
        
        return distribution
    
    def _calculate_seller_commission(self, seller_membership: TeamMembership) -> Decimal:
        """
        Calcula la comisión total que recibe quien hace la venta
        (su nivel + todos los niveles inferiores)
        """
        seller_level = seller_membership.position_type.hierarchy_level
        positions_covered = self._get_positions_at_or_below(seller_level)
        
        total_commission = Decimal('0')
        for position_code in positions_covered:
            commission = self.commission_structure.get_commission_for_position(position_code)
            total_commission += Decimal(str(commission))
        
        return total_commission
    
    def _get_positions_at_or_below(self, hierarchy_level: int) -> List[str]:
        """Obtiene códigos de posiciones en el nivel dado o inferiores"""
        return [
            code for code, level in self.position_hierarchy.items() 
            if level >= hierarchy_level
        ]
    
    def _calculate_supervisor_commissions(self, seller_membership: TeamMembership, sale_amount: Decimal) -> Dict:
        """
        Calcula comisiones para supervisores del vendedor
        """
        supervisor_distributions = {}
        
        # Obtener cadena de supervisión hacia arriba
        supervision_chain = self._get_supervision_chain(seller_membership)
        
        for supervisor_relation in supervision_chain:
            supervisor_membership = supervisor_relation.supervisor_membership
            
            if supervisor_relation.relation_type == 'DIRECT':
                # Supervisión directa: recibe comisiones de niveles saltados
                commission = self._calculate_direct_supervision_commission(
                    seller_membership, 
                    supervisor_membership,
                    supervisor_relation
                )
            else:
                # Supervisión normal: recibe su comisión normal
                commission = self.commission_structure.get_commission_for_position(
                    supervisor_membership.position_type.code
                )
            
            if commission > 0:
                supervisor_distributions[supervisor_membership.user.id] = {
                    'user': supervisor_membership.user,
                    'membership': supervisor_membership,
                    'percentage': Decimal(str(commission)),
                    'amount': sale_amount * (Decimal(str(commission)) / 100),
                    'reason': f'Supervisión {supervisor_relation.get_relation_type_display()}',
                    'relation_type': supervisor_relation.relation_type
                }
        
        return supervisor_distributions
    
    def _get_supervision_chain(self, membership: TeamMembership) -> List[HierarchyRelation]:
        """
        Obtiene la cadena de supervisión hacia arriba para una membresía
        """
        chain = []
        current_membership = membership
        visited_memberships = set()  # Para evitar ciclos infinitos
        
        while current_membership and current_membership.id not in visited_memberships:
            visited_memberships.add(current_membership.id)
            
            # Buscar supervisor directo (prioridad a supervisión directa)
            supervisor_relations = HierarchyRelation.objects.filter(
                subordinate_membership=current_membership,
                is_active=True
            ).order_by('relation_type')  # DIRECT aparece antes que NORMAL
            
            supervisor_relation = supervisor_relations.first()
            if supervisor_relation:
                chain.append(supervisor_relation)
                current_membership = supervisor_relation.supervisor_membership
            else:
                break
        
        return chain
    
    def _calculate_direct_supervision_commission(
        self, 
        seller_membership: TeamMembership,
        supervisor_membership: TeamMembership, 
        relation: HierarchyRelation
    ) -> Decimal:
        """
        Calcula comisión para supervisión directa (acumula niveles saltados)
        """
        seller_level = seller_membership.position_type.hierarchy_level
        supervisor_level = supervisor_membership.position_type.hierarchy_level
        
        # Niveles saltados (entre supervisor y subordinado)
        skipped_levels = []
        for code, level in self.position_hierarchy.items():
            if supervisor_level < level < seller_level:
                skipped_levels.append(code)
        
        # Comisión del supervisor + comisiones de niveles saltados
        total_commission = self.commission_structure.get_commission_for_position(
            supervisor_membership.position_type.code
        )
        
        for skipped_position in skipped_levels:
            total_commission += self.commission_structure.get_commission_for_position(skipped_position)
        
        return Decimal(str(total_commission))


class HierarchyAnalyzer:
    """
    Analizador de jerarquías para reportes y consultas complejas
    """
    
    @staticmethod
    def get_team_hierarchy_tree(organizational_unit):
        """
        Obtiene el árbol jerárquico completo de una unidad organizacional
        """
        memberships = TeamMembership.objects.filter(
            organizational_unit=organizational_unit,
            is_active=True,
            status='ACTIVE'
        ).select_related('user', 'position_type')
        
        # Construir árbol jerárquico
        hierarchy_tree = {}
        
        for membership in memberships:
            # Obtener subordinados
            subordinates = HierarchyRelation.objects.filter(
                supervisor_membership=membership,
                is_active=True
            ).select_related('subordinate_membership__user', 'subordinate_membership__position_type')
            
            hierarchy_tree[membership.id] = {
                'membership': membership,
                'subordinates': [
                    {
                        'membership': rel.subordinate_membership,
                        'relation_type': rel.relation_type,
                        'authority_level': rel.authority_level
                    }
                    for rel in subordinates
                ]
            }
        
        return hierarchy_tree
    
    @staticmethod
    def get_user_reporting_structure(user, organizational_unit=None):
        """
        Obtiene la estructura de reporte completa de un usuario
        """
        memberships = user.team_memberships.filter(is_active=True, status='ACTIVE')
        if organizational_unit:
            memberships = memberships.filter(organizational_unit=organizational_unit)
        
        reporting_structure = {}
        
        for membership in memberships:
            # Supervisores
            supervisors = HierarchyRelation.objects.filter(
                subordinate_membership=membership,
                is_active=True
            ).select_related('supervisor_membership__user', 'supervisor_membership__position_type')
            
            # Subordinados
            subordinates = HierarchyRelation.objects.filter(
                supervisor_membership=membership,
                is_active=True
            ).select_related('subordinate_membership__user', 'subordinate_membership__position_type')
            
            reporting_structure[membership.organizational_unit.name] = {
                'membership': membership,
                'supervisors': [
                    {
                        'user': rel.supervisor_membership.user,
                        'position': rel.supervisor_membership.position_type.name,
                        'relation_type': rel.relation_type,
                        'authority_level': rel.authority_level
                    }
                    for rel in supervisors
                ],
                'subordinates': [
                    {
                        'user': rel.subordinate_membership.user,
                        'position': rel.subordinate_membership.position_type.name,
                        'relation_type': rel.relation_type,
                        'authority_level': rel.authority_level
                    }
                    for rel in subordinates
                ]
            }
        
        return reporting_structure
    
    @staticmethod
    def find_potential_conflicts(organizational_unit):
        """
        Identifica potenciales conflictos en la estructura jerárquica
        """
        conflicts = []
        
        # Buscar ciclos en jerarquía
        memberships = TeamMembership.objects.filter(
            organizational_unit=organizational_unit,
            is_active=True
        )
        
        for membership in memberships:
            if HierarchyAnalyzer._has_circular_reporting(membership):
                conflicts.append({
                    'type': 'CIRCULAR_REPORTING',
                    'membership': membership,
                    'description': f'Usuario {membership.user.username} tiene reporte circular'
                })
        
        # Buscar múltiples supervisores primarios
        for membership in memberships:
            primary_supervisors = HierarchyRelation.objects.filter(
                subordinate_membership=membership,
                is_primary=True,
                is_active=True
            ).count()
            
            if primary_supervisors > 1:
                conflicts.append({
                    'type': 'MULTIPLE_PRIMARY_SUPERVISORS',
                    'membership': membership,
                    'description': f'Usuario {membership.user.username} tiene {primary_supervisors} supervisores primarios'
                })
        
        return conflicts
    
    @staticmethod
    def _has_circular_reporting(membership, visited=None):
        """Verifica si existe reporte circular"""
        if visited is None:
            visited = set()
        
        if membership.id in visited:
            return True
        
        visited.add(membership.id)
        
        supervisors = HierarchyRelation.objects.filter(
            subordinate_membership=membership,
            is_active=True
        )
        
        for supervisor_rel in supervisors:
            if HierarchyAnalyzer._has_circular_reporting(supervisor_rel.supervisor_membership, visited.copy()):
                return True
        
        return False


# Funciones de utilidad
def get_commission_preview(sale_amount, seller_membership):
    """
    Obtiene preview de distribución de comisiones sin guardar
    """
    commission_structure = CommissionStructure.objects.filter(
        organizational_unit=seller_membership.organizational_unit,
        is_active=True
    ).first()
    
    if not commission_structure:
        return {'error': 'No hay estructura de comisiones configurada'}
    
    calculator = CommissionCalculator(commission_structure)
    return calculator.calculate_distribution(Decimal(str(sale_amount)), seller_membership)


def validate_hierarchy_consistency(organizational_unit):
    """
    Valida consistencia de jerarquía en una unidad organizacional
    """
    analyzer = HierarchyAnalyzer()
    return analyzer.find_potential_conflicts(organizational_unit)