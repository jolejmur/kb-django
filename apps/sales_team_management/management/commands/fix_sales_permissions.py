# apps/sales/management/commands/fix_sales_permissions.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.sales_team_management.models import (
    EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
    GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
    ComisionDesarrollo, ComisionVenta, AsignacionEquipoProyecto
)


class Command(BaseCommand):
    help = 'Verifica y crea permisos faltantes para el módulo de sales'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Verificando permisos del módulo sales...'))

        models_to_check = [
            EquipoVenta, GerenteEquipo, JefeVenta, TeamLeader, Vendedor,
            GerenteProyecto, JefeProyecto, Proyecto, Inmueble,
            ComisionDesarrollo, ComisionVenta, AsignacionEquipoProyecto
        ]

        for model in models_to_check:
            self.check_model_permissions(model)

        # Ejecutar syncdb para asegurar que todos los permisos estén creados
        from django.core.management import call_command
        self.stdout.write('🔄 Ejecutando syncdb para generar permisos...')
        call_command('migrate', '--run-syncdb', verbosity=0)

        self.stdout.write(self.style.SUCCESS('✅ Verificación de permisos completada!'))

    def check_model_permissions(self, model):
        """Verifica y reporta permisos para un modelo específico"""
        content_type = ContentType.objects.get_for_model(model)

        self.stdout.write(f"\n📋 Modelo: {model.__name__}")
        self.stdout.write(f"   App: {content_type.app_label}")

        # Verificar permisos estándar de Django
        standard_permissions = ['add', 'change', 'delete', 'view']

        for perm_type in standard_permissions:
            codename = f"{perm_type}_{model.__name__.lower()}"
            full_codename = f"{content_type.app_label}.{codename}"

            try:
                permission = Permission.objects.get(
                    content_type=content_type,
                    codename=codename
                )
                self.stdout.write(f"   ✅ {full_codename}")
            except Permission.DoesNotExist:
                self.stdout.write(f"   ❌ {full_codename} (FALTANTE)")

                # Crear permiso faltante
                permission = Permission.objects.create(
                    content_type=content_type,
                    codename=codename,
                    name=f'Can {perm_type} {model._meta.verbose_name}'
                )
                self.stdout.write(f"   🆕 Creado: {full_codename}")

        return True