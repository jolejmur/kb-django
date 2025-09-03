# apps/communications/lead_distribution_service.py
from django.utils import timezone
from decimal import Decimal
from .models import LeadDistributionConfig, LeadAssignment, Lead
import logging

logger = logging.getLogger(__name__)


class LeadDistributionService:
    """
    Servicio para distribuir leads usando algoritmo de Contador Acumulativo
    """
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def get_next_sales_force_for_lead(self, lead=None):
        """
        Algoritmo de Contador Acumulativo:
        
        1. Obtiene fuerzas de venta elegibles (activas + dentro de límites)
        2. Calcula total de leads asignados HOY
        3. Para cada fuerza: calcula cuántos DEBERÍA tener vs cuántos TIENE
        4. Asigna al que tenga mayor DÉFICIT
        
        Returns:
            LeadDistributionConfig o None
        """
        try:
            # 1. Obtener configuraciones elegibles
            eligible_configs = self._get_eligible_configs()
            
            if not eligible_configs:
                logger.warning("No hay fuerzas de venta elegibles para recibir leads")
                return None
            
            # 2. Obtener total de leads asignados HOY
            total_leads_today = LeadAssignment.objects.filter(
                assigned_date__date=self.today,
                is_active=True
            ).count()
            
            # 3. Calcular déficits y encontrar el ganador
            best_config = None
            max_deficit = -999999  # Empezar con valor muy bajo
            
            logger.info(f"Calculando distribución para lead #{total_leads_today + 1}")
            
            for config in eligible_configs:
                # Lo que DEBERÍA tener después de asignar este lead
                expected_after_assignment = (
                    float(config.distribution_percentage) / 100
                ) * (total_leads_today + 1)
                
                # Lo que TIENE actualmente
                current_leads = config.current_leads_today
                
                # Su déficit después de la asignación
                deficit = expected_after_assignment - current_leads
                
                logger.info(
                    f"  {config.organizational_unit.name}: "
                    f"{config.distribution_percentage}% | "
                    f"Debería: {expected_after_assignment:.2f} | "
                    f"Tiene: {current_leads} | "
                    f"Déficit: {deficit:.2f}"
                )
                
                # Elegir el que tenga mayor déficit
                if deficit > max_deficit:
                    max_deficit = deficit
                    best_config = config
            
            if best_config:
                logger.info(
                    f"✓ Elegido: {best_config.organizational_unit.name} "
                    f"(déficit: {max_deficit:.2f})"
                )
            else:
                logger.error("No se pudo determinar fuerza de venta ganadora")
            
            return best_config
            
        except Exception as e:
            logger.error(f"Error en algoritmo de distribución: {str(e)}")
            return None
    
    def _get_eligible_configs(self):
        """
        Obtiene configuraciones elegibles para recibir leads:
        - Activas para leads
        - Dentro de límites diarios/semanales
        - Ordenadas por nombre de unidad organizacional
        """
        configs = LeadDistributionConfig.objects.filter(
            is_active_for_leads=True
        ).select_related('organizational_unit').order_by('organizational_unit__name')
        
        eligible = []
        for config in configs:
            if config.can_receive_more_leads:
                eligible.append(config)
            else:
                logger.info(
                    f"Saltando {config.organizational_unit.name}: "
                    f"límites alcanzados (día: {config.current_leads_today}/"
                    f"{config.max_leads_per_day or '∞'}, "
                    f"semana: {config.current_leads_this_week}/"
                    f"{config.max_leads_per_week or '∞'})"
                )
        
        return eligible
    
    def assign_lead_to_sales_force(self, lead, assigned_by_user=None, assignment_type='AUTOMATIC'):
        """
        Asigna un lead a una fuerza de venta usando el algoritmo
        
        Args:
            lead: Instancia de Lead
            assigned_by_user: Usuario que realiza la asignación (opcional para asignaciones automáticas)
            assignment_type: Tipo de asignación (AUTOMATIC, MANUAL, etc.)
            
        Returns:
            LeadAssignment o None
        """
        try:
            # 1. Obtener fuerza de venta usando el algoritmo
            selected_config = self.get_next_sales_force_for_lead(lead)
            
            if not selected_config:
                logger.warning(f"No se pudo asignar lead #{lead.id}: no hay fuerzas disponibles")
                return None
            
            # 2. Crear la asignación
            assignment = LeadAssignment.objects.create(
                lead=lead,
                organizational_unit=selected_config.organizational_unit,
                assignment_type=assignment_type,
                status='ASSIGNED',
                assigned_by=assigned_by_user,  # Puede ser None para asignaciones automáticas
                notes=f'Asignado {"automáticamente" if assigned_by_user is None else "manualmente"} '
                      f'usando algoritmo de Contador Acumulativo. '
                      f'Déficit: {self._calculate_deficit(selected_config):.2f}'
            )
            
            logger.info(
                f"✓ Lead #{lead.id} asignado a {selected_config.organizational_unit.name} "
                f"(Assignment #{assignment.id})"
            )
            
            return assignment
            
        except Exception as e:
            logger.error(f"Error asignando lead #{lead.id}: {str(e)}")
            return None
    
    def _calculate_deficit(self, config):
        """Calcula el déficit actual de una configuración"""
        total_today = LeadAssignment.objects.filter(
            assigned_date__date=self.today,
            is_active=True
        ).count()
        
        expected = (float(config.distribution_percentage) / 100) * total_today
        actual = config.current_leads_today
        
        return expected - actual
    
    def simulate_distribution(self, num_leads=100):
        """
        Simula la distribución de N leads para testing
        
        Args:
            num_leads: Número de leads a simular
            
        Returns:
            dict con resultados de la simulación
        """
        # Obtener configuraciones activas
        active_configs = LeadDistributionConfig.objects.filter(
            is_active_for_leads=True
        ).order_by('organizational_unit__name')
        
        if not active_configs:
            return {'error': 'No hay configuraciones activas'}
        
        # Resetear contadores para simulación
        simulation_results = {}
        for config in active_configs:
            simulation_results[config.organizational_unit.name] = {
                'config': config,
                'expected_percentage': float(config.distribution_percentage),
                'assigned_count': 0,
                'final_percentage': 0.0,
                'assignments': []  # Para tracking detallado
            }
        
        # Simular asignación lead por lead
        for lead_num in range(1, num_leads + 1):
            # Calcular déficits actuales
            best_unit = None
            max_deficit = -999999
            
            for unit_name, data in simulation_results.items():
                config = data['config']
                
                # Lo que debería tener
                expected = (data['expected_percentage'] / 100) * lead_num
                
                # Lo que tiene
                current = data['assigned_count']
                
                # Déficit
                deficit = expected - current
                
                if deficit > max_deficit:
                    max_deficit = deficit
                    best_unit = unit_name
            
            # Asignar al ganador
            if best_unit:
                simulation_results[best_unit]['assigned_count'] += 1
                simulation_results[best_unit]['assignments'].append({
                    'lead_number': lead_num,
                    'deficit': max_deficit
                })
        
        # Calcular porcentajes finales
        for unit_name, data in simulation_results.items():
            data['final_percentage'] = (data['assigned_count'] / num_leads) * 100
            data['accuracy'] = 100 - abs(data['expected_percentage'] - data['final_percentage'])
        
        return {
            'total_leads': num_leads,
            'results': simulation_results,
            'summary': {
                'total_assigned': sum(data['assigned_count'] for data in simulation_results.values()),
                'average_accuracy': sum(data['accuracy'] for data in simulation_results.values()) / len(simulation_results)
            }
        }
    
    def get_current_distribution_stats(self):
        """
        Obtiene estadísticas actuales de distribución para el día
        """
        total_today = LeadAssignment.objects.filter(
            assigned_date__date=self.today,
            is_active=True
        ).count()
        
        if total_today == 0:
            return {'message': 'No hay leads asignados hoy'}
        
        active_configs = LeadDistributionConfig.objects.filter(
            is_active_for_leads=True
        )
        
        stats = {}
        for config in active_configs:
            current_leads = config.current_leads_today
            expected_leads = (float(config.distribution_percentage) / 100) * total_today
            deficit = expected_leads - current_leads
            
            stats[config.organizational_unit.name] = {
                'expected_percentage': float(config.distribution_percentage),
                'current_count': current_leads,
                'expected_count': expected_leads,
                'actual_percentage': (current_leads / total_today * 100) if total_today > 0 else 0,
                'deficit': deficit,
                'accuracy': 100 - abs(float(config.distribution_percentage) - 
                                    (current_leads / total_today * 100)) if total_today > 0 else 0
            }
        
        return {
            'total_leads_today': total_today,
            'stats': stats,
            'date': self.today.isoformat()
        }