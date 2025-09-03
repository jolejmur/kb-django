# apps/communications/management/commands/test_lead_distribution.py
from django.core.management.base import BaseCommand
from apps.communications.lead_distribution_service import LeadDistributionService
from apps.communications.models import LeadDistributionConfig
from apps.sales_team_management.models import OrganizationalUnit


class Command(BaseCommand):
    help = 'Prueba el algoritmo de distribución de leads con simulaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leads', 
            type=int, 
            default=100, 
            help='Número de leads a simular (default: 100)'
        )
        parser.add_argument(
            '--setup-demo', 
            action='store_true', 
            help='Configura datos de demostración automáticamente'
        )
        parser.add_argument(
            '--current-stats', 
            action='store_true', 
            help='Muestra estadísticas actuales de distribución'
        )

    def handle(self, *args, **options):
        service = LeadDistributionService()
        
        # Configurar datos de demo si se solicita
        if options['setup_demo']:
            self.setup_demo_data()
        
        # Mostrar estadísticas actuales si se solicita
        if options['current_stats']:
            self.show_current_stats(service)
            return
        
        # Verificar que hay configuraciones activas
        active_configs = LeadDistributionConfig.objects.filter(is_active_for_leads=True)
        
        if not active_configs:
            self.stdout.write(
                self.style.ERROR('❌ No hay configuraciones activas para distribuir leads')
            )
            self.stdout.write('Usa --setup-demo para crear datos de ejemplo')
            return
        
        # Mostrar configuración actual
        self.show_current_config(active_configs)
        
        # Ejecutar simulación
        num_leads = options['leads']
        self.stdout.write(f'\n🧪 Simulando distribución de {num_leads} leads...')
        
        results = service.simulate_distribution(num_leads)
        
        if 'error' in results:
            self.stdout.write(self.style.ERROR(f'❌ {results["error"]}'))
            return
        
        # Mostrar resultados
        self.show_simulation_results(results)

    def setup_demo_data(self):
        """Configura datos de demostración"""
        self.stdout.write('⚙️  Configurando datos de demostración...')
        
        # Buscar o crear unidades organizacionales de tipo SALES
        demo_units = [
            {'name': 'Fuerza Venta Alpha', 'percentage': 40},
            {'name': 'Fuerza Venta Beta', 'percentage': 35},
            {'name': 'Fuerza Venta Gamma', 'percentage': 25},
        ]
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            self.stdout.write(self.style.ERROR('❌ No se encontró usuario admin'))
            return
        
        for unit_data in demo_units:
            # Crear o obtener unidad organizacional
            unit, created = OrganizationalUnit.objects.get_or_create(
                name=unit_data['name'],
                defaults={
                    'unit_type': 'SALES',
                    'description': f'Unidad de demostración - {unit_data["percentage"]}%',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Creada unidad: {unit.name}')
            
            # Crear o actualizar configuración de distribución
            config, created = LeadDistributionConfig.objects.get_or_create(
                organizational_unit=unit,
                defaults={
                    'created_by': admin_user,
                    'last_modified_by': admin_user,
                }
            )
            
            # Actualizar configuración
            config.is_active_for_leads = True
            config.distribution_percentage = unit_data['percentage']
            config.last_modified_by = admin_user
            config.save()
            
            action = 'Creada' if created else 'Actualizada'
            self.stdout.write(f'  ✓ {action} configuración: {unit.name} → {unit_data["percentage"]}%')
        
        self.stdout.write(self.style.SUCCESS('✅ Datos de demostración configurados'))

    def show_current_config(self, configs):
        """Muestra la configuración actual"""
        self.stdout.write('\n📊 Configuración Actual:')
        self.stdout.write('─' * 60)
        
        total_percentage = 0
        for config in configs:
            total_percentage += float(config.distribution_percentage)
            
            limits = []
            if config.max_leads_per_day:
                limits.append(f'{config.max_leads_per_day}/día')
            if config.max_leads_per_week:
                limits.append(f'{config.max_leads_per_week}/sem')
            
            limits_str = f' (límites: {", ".join(limits)})' if limits else ''
            
            self.stdout.write(
                f'  • {config.organizational_unit.name}: '
                f'{config.distribution_percentage}%{limits_str}'
            )
        
        # Verificar que suma 100%
        if abs(total_percentage - 100) < 0.01:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Total: {total_percentage}%'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠ Total: {total_percentage}% (no suma 100%)'))

    def show_simulation_results(self, results):
        """Muestra los resultados de la simulación"""
        self.stdout.write('\n📈 Resultados de la Simulación:')
        self.stdout.write('═' * 80)
        
        # Encabezado de tabla
        self.stdout.write(
            f"{'Fuerza de Venta':<25} {'Esperado':<12} {'Obtenido':<12} {'Precisión':<12} {'Diferencia':<12}"
        )
        self.stdout.write('─' * 80)
        
        # Resultados por fuerza de venta
        for unit_name, data in results['results'].items():
            expected_pct = data['expected_percentage']
            final_pct = data['final_percentage']
            accuracy = data['accuracy']
            difference = final_pct - expected_pct
            
            # Colores basados en precisión
            if accuracy >= 99:
                style = self.style.SUCCESS
            elif accuracy >= 95:
                style = self.style.WARNING
            else:
                style = self.style.ERROR
            
            self.stdout.write(style(
                f"{unit_name:<25} "
                f"{expected_pct:>8.1f}%   "
                f"{final_pct:>8.1f}%   "
                f"{accuracy:>8.1f}%   "
                f"{difference:>+8.1f}%"
            ))
        
        # Resumen
        summary = results['summary']
        self.stdout.write('─' * 80)
        self.stdout.write(
            f"Total leads asignados: {summary['total_assigned']}/{results['total_leads']}"
        )
        self.stdout.write(
            f"Precisión promedio: {summary['average_accuracy']:.1f}%"
        )
        
        # Interpretación
        self.stdout.write('\n📝 Interpretación:')
        if summary['average_accuracy'] >= 99:
            self.stdout.write(self.style.SUCCESS('  🎯 ¡Excelente! Distribución casi perfecta'))
        elif summary['average_accuracy'] >= 95:
            self.stdout.write(self.style.SUCCESS('  ✅ Muy buena distribución'))
        elif summary['average_accuracy'] >= 90:
            self.stdout.write(self.style.WARNING('  ⚠️  Distribución aceptable'))
        else:
            self.stdout.write(self.style.ERROR('  ❌ Distribución necesita ajustes'))
        
        # Mostrar primeras asignaciones para verificar algoritmo
        self.stdout.write('\n🔍 Primeras 10 asignaciones:')
        first_assignments = {}
        for unit_name, data in results['results'].items():
            for assignment in data['assignments'][:10]:
                lead_num = assignment['lead_number']
                if lead_num not in first_assignments:
                    first_assignments[lead_num] = unit_name
        
        for lead_num in sorted(first_assignments.keys())[:10]:
            unit_name = first_assignments[lead_num]
            self.stdout.write(f'  Lead #{lead_num:2d} → {unit_name}')

    def show_current_stats(self, service):
        """Muestra estadísticas actuales del día"""
        self.stdout.write('📊 Estadísticas Actuales de Distribución')
        self.stdout.write('═' * 60)
        
        stats = service.get_current_distribution_stats()
        
        if 'message' in stats:
            self.stdout.write(self.style.WARNING(f'ℹ️  {stats["message"]}'))
            return
        
        self.stdout.write(f'📅 Fecha: {stats["date"]}')
        self.stdout.write(f'📊 Total leads hoy: {stats["total_leads_today"]}')
        self.stdout.write('─' * 60)
        
        # Tabla de estadísticas
        self.stdout.write(
            f"{'Fuerza de Venta':<25} {'Esperado':<10} {'Real':<10} {'Déficit':<10} {'Precisión':<10}"
        )
        self.stdout.write('─' * 60)
        
        for unit_name, unit_stats in stats['stats'].items():
            expected_count = unit_stats['expected_count']
            current_count = unit_stats['current_count']
            deficit = unit_stats['deficit']
            accuracy = unit_stats['accuracy']
            
            # Colorear según precisión
            if accuracy >= 95:
                style = self.style.SUCCESS
            elif accuracy >= 85:
                style = self.style.WARNING
            else:
                style = self.style.ERROR
            
            self.stdout.write(style(
                f"{unit_name:<25} "
                f"{expected_count:>6.1f}   "
                f"{current_count:>6d}   "
                f"{deficit:>+6.1f}   "
                f"{accuracy:>6.1f}%"
            ))
        
        # Próxima recomendación
        max_deficit_unit = max(
            stats['stats'].items(), 
            key=lambda x: x[1]['deficit']
        )
        
        self.stdout.write('─' * 60)
        self.stdout.write(
            f"🎯 Próximo lead debería ir a: {max_deficit_unit[0]} "
            f"(déficit: {max_deficit_unit[1]['deficit']:+.1f})"
        )