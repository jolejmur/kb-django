# apps/events/management/commands/regenerate_qr_codes.py

from django.core.management.base import BaseCommand
from apps.events.models import InvitacionQR

class Command(BaseCommand):
    help = 'Regenera todos los códigos QR con la nueva información completa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la regeneración incluso si ya existe archivo QR',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Regenerando códigos QR con información completa...'))

        # Obtener todas las invitaciones QR
        invitaciones = InvitacionQR.objects.select_related('evento', 'vendedor').all()
        
        if not invitaciones.exists():
            self.stdout.write(self.style.WARNING('  ⚠️  No se encontraron códigos QR para regenerar'))
            return

        total = invitaciones.count()
        regenerados = 0
        errores = 0

        for i, invitacion in enumerate(invitaciones, 1):
            try:
                # Mostrar progreso
                self.stdout.write(f"  📋 Procesando {i}/{total}: {invitacion.evento.nombre} - {invitacion.vendedor.get_full_name() or invitacion.vendedor.username}")
                
                # Forzar regeneración si se solicita o si no existe archivo
                if options['force'] or not invitacion.archivo_qr:
                    # Eliminar archivo anterior si existe
                    if invitacion.archivo_qr:
                        try:
                            invitacion.archivo_qr.delete(save=False)
                        except:
                            pass
                    
                    # Regenerar QR
                    invitacion.generar_qr()
                    regenerados += 1
                    self.stdout.write(f"    ✅ QR regenerado para: {invitacion}")
                else:
                    self.stdout.write(f"    ⏭️  QR ya existe para: {invitacion}")
                    
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f"    ❌ Error al regenerar QR para {invitacion}: {str(e)}")
                )

        # Resumen final
        self.stdout.write(self.style.SUCCESS(f"\n📊 RESUMEN:"))
        self.stdout.write(f"  📈 Total invitaciones: {total}")
        self.stdout.write(f"  ✅ QRs regenerados: {regenerados}")
        self.stdout.write(f"  ⏭️  QRs sin cambios: {total - regenerados - errores}")
        self.stdout.write(f"  ❌ Errores: {errores}")
        
        if errores == 0:
            self.stdout.write(self.style.SUCCESS('\n🎉 ¡Todos los códigos QR han sido regenerados exitosamente!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Proceso completado con {errores} errores.'))
        
        self.stdout.write(self.style.SUCCESS('\nℹ️  Los nuevos QRs ahora contienen:'))
        self.stdout.write('  🎪 Nombre del evento')
        self.stdout.write('  📍 Ubicación del evento') 
        self.stdout.write('  📅 Fecha y hora')
        self.stdout.write('  👤 Nombre del agente')
        self.stdout.write('  👥 Equipo de ventas')
        self.stdout.write('  🔗 Enlace al sistema')