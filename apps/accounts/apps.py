# apps/accounts/apps.py - REEMPLAZAR COMPLETAMENTE

from django.apps import AppConfig
import os
import sys


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Accounts'

    def ready(self):
        """Se ejecuta cuando la app está lista"""
        # Solo ejecutar en el servidor de desarrollo, no en comandos
        if self.should_run_auto_setup():
            # Usar threading para evitar el warning de acceso a DB durante inicialización
            import threading
            threading.Timer(0.1, self.setup_basic_menu_delayed).start()

    def should_run_auto_setup(self):
        """Determina si debe ejecutar la configuración automática"""
        # Solo en el proceso principal del servidor de desarrollo
        if os.environ.get('RUN_MAIN') != 'true':
            return False

        # No ejecutar en ciertos comandos
        if len(sys.argv) > 1:
            command = sys.argv[1]
            skip_commands = [
                'migrate', 'makemigrations', 'showmigrations',
                'sqlmigrate', 'squashmigrations', 'collectstatic',
                'check', 'test', 'shell', 'dbshell', 'createsuperuser'
            ]
            if command in skip_commands:
                return False

        return True

    def setup_basic_menu_delayed(self):
        """Configura el menú básico con un pequeño delay para evitar warnings"""
        try:
            from django.core.management import call_command
            from django.db import connection
            from django.db.utils import OperationalError
            from django.contrib.auth.models import Group

            # Verificar que las tablas existan
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                                   SELECT name
                                   FROM sqlite_master
                                   WHERE type = 'table'
                                     AND name IN (
                                                  'accounts_menucategory',
                                                  'accounts_navigation',
                                                  'auth_group',
                                                  'accounts_role'
                                       );
                                   """)
                    tables = [row[0] for row in cursor.fetchall()]

                    if len(tables) >= 4:
                        # Verificar si ya existe la configuración básica
                        basic_groups = ['Gestión de Módulos', 'Gestión de Roles', 'Gestión de Usuarios']
                        existing_groups = Group.objects.filter(name__in=basic_groups)

                        if existing_groups.count() < 3:
                            print("\n" + "=" * 60)
                            print("🚀 DJANGO CRM - CONFIGURACIÓN AUTOMÁTICA")
                            print("=" * 60)
                            print("⚙️  Creando estructura básica del sistema...")

                            # Ejecutar el comando que ya funciona bien
                            call_command('setup_default_menu', verbosity=1)

                            print("✅ ¡Sistema básico configurado exitosamente!")
                            print("📦 Se crearon 3 grupos administrativos:")
                            print("   • Gestión de Módulos")
                            print("   • Gestión de Roles")
                            print("   • Gestión de Usuarios")
                            print("🔗 Navegación del sidebar configurada")
                            print("👤 Permisos asignados al superadmin")
                            print("=" * 60)
                            print("🌟 ¡Listo para usar! Accede con tu superusuario")
                            print("=" * 60 + "\n")
                        else:
                            # Configuración ya existe, mensaje más discreto
                            print("✅ Sistema CRM ya configurado - Listo para usar")

            except OperationalError:
                # Las tablas no existen (primera migración pendiente)
                print("⚠️  Base de datos no inicializada. Ejecuta 'python manage.py migrate' primero.")

        except Exception as e:
            print(f"❌ Error en configuración automática: {e}")
            print("💡 Puedes ejecutar manualmente: python manage.py setup_default_menu --clean")