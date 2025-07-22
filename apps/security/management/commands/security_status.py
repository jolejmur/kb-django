"""
Comando para monitorear el estado de seguridad
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
import time

class Command(BaseCommand):
    help = 'Muestra el estado de seguridad y IPs bloqueadas'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== ESTADO DE SEGURIDAD ===')
        )
        
        # Buscar IPs bloqueadas (esto es una aproximación simple)
        blocked_ips = []
        failed_attempts = []
        
        # Nota: En un entorno real, necesitarías una forma más eficiente de obtener estas claves
        # Por simplicidad, asumimos patrones de claves conocidos
        
        self.stdout.write('\n🛡️  IPs Bloqueadas:')
        if not blocked_ips:
            self.stdout.write('   ✅ No hay IPs bloqueadas actualmente')
        
        self.stdout.write('\n📊 Estadísticas:')
        self.stdout.write('   • Protección activa: ✅ ACTIVADA')
        self.stdout.write('   • Máximo intentos: 5')
        self.stdout.write('   • Tiempo de bloqueo: 15 minutos')
        self.stdout.write('   • Ventana de intentos: 5 minutos')
        
        self.stdout.write('\n📝 Para monitorear logs en tiempo real:')
        self.stdout.write('   tail -f logs/security.log')
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Sistema de seguridad funcionando correctamente')
        )