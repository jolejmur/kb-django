from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.sales_team_management.models import HierarchyRelation, TeamMembership
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Elimina todas las relaciones jerárquicas y usuarios excepto admin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la eliminación',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué se eliminaría sin hacer cambios',
        )

    def handle(self, *args, **options):
        self.stdout.write("=== ANÁLISIS ACTUAL ===")
        
        # Estadísticas actuales
        total_users = User.objects.count()
        admin_users = User.objects.filter(username='admin').count()
        regular_users = User.objects.exclude(username='admin').count()
        total_memberships = TeamMembership.objects.count()
        total_relations = HierarchyRelation.objects.count()
        
        self.stdout.write(f"👥 Usuarios totales: {total_users}")
        self.stdout.write(f"   - Admin: {admin_users}")
        self.stdout.write(f"   - Regulares: {regular_users}")
        self.stdout.write(f"🔗 Membresías de equipo: {total_memberships}")
        self.stdout.write(f"📊 Relaciones jerárquicas: {total_relations}")
        
        # Verificar que admin existe
        admin_user = User.objects.filter(username='admin').first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR("❌ ERROR: Usuario admin no encontrado. Abortando.")
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Usuario admin confirmado: {admin_user.username}")
        )
        
        if total_memberships == 0 and total_relations == 0 and regular_users == 0:
            self.stdout.write(self.style.SUCCESS("✅ No hay datos para limpiar."))
            return
        
        # Mostrar qué se va a eliminar
        self.stdout.write(f"\n⚠️  ESTA OPERACIÓN ELIMINARÁ:")
        self.stdout.write(f"   - {total_relations} relaciones jerárquicas")
        self.stdout.write(f"   - {total_memberships} membresías de equipo")
        self.stdout.write(f"   - {regular_users} usuarios (excepto admin)")
        
        self.stdout.write(f"\n✅ SE MANTENDRÁN INTACTOS:")
        self.stdout.write(f"   - Equipos (OrganizationalUnit)")
        self.stdout.write(f"   - Tipos de posiciones (PositionType)")
        self.stdout.write(f"   - Roles y permisos")
        self.stdout.write(f"   - Módulos del sistema")
        self.stdout.write(f"   - Usuario admin")
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN: No se realizarán cambios reales.")
            )
            return
        
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'Usa --confirm para proceder con la eliminación.\n'
                    'Usa --dry-run para solo ver qué se eliminaría.'
                )
            )
            return
        
        # Realizar eliminación en transacción
        try:
            with transaction.atomic():
                self.stdout.write("\n🧹 Iniciando limpieza...")
                
                # Paso 1: Eliminar relaciones jerárquicas
                self.stdout.write("1️⃣ Eliminando relaciones jerárquicas...")
                relations_deleted = HierarchyRelation.objects.all().delete()
                self.stdout.write(f"   ✅ Eliminadas {relations_deleted[0]} relaciones")
                
                # Paso 2: Eliminar membresías
                self.stdout.write("2️⃣ Eliminando membresías de equipo...")
                memberships_deleted = TeamMembership.objects.all().delete()
                self.stdout.write(f"   ✅ Eliminadas {memberships_deleted[0]} membresías")
                
                # Paso 3: Eliminar usuarios (excepto admin)
                self.stdout.write("3️⃣ Eliminando usuarios (excepto admin)...")
                users_deleted = User.objects.exclude(username='admin').delete()
                self.stdout.write(f"   ✅ Eliminados {users_deleted[0]} usuarios")
                
                # Verificar resultado
                final_users = User.objects.count()
                final_memberships = TeamMembership.objects.count()
                final_relations = HierarchyRelation.objects.count()
                
                self.stdout.write(f"\n=== RESULTADO FINAL ===")
                self.stdout.write(f"👥 Usuarios restantes: {final_users}")
                self.stdout.write(f"🔗 Membresías restantes: {final_memberships}")
                self.stdout.write(f"📊 Relaciones restantes: {final_relations}")
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Limpieza completada exitosamente!\n"
                        f"Total eliminado: {users_deleted[0]} usuarios + "
                        f"{memberships_deleted[0]} membresías + {relations_deleted[0]} relaciones"
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error durante la limpieza: {e}")
            )
            raise