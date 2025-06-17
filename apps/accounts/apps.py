from django.apps import AppConfig
import os


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Accounts'

    def ready(self):
        """Se ejecuta cuando la app está lista"""
        # Solo ejecutar en el proceso principal del servidor de desarrollo
        if os.environ.get('RUN_MAIN') or os.environ.get('DJANGO_SETTINGS_MODULE'):
            self.setup_default_menu()

    def setup_default_menu(self):
        """Configura automáticamente el menú por defecto"""
        try:
            # Verificar que las tablas existan antes de ejecutar
            from django.db import connection
            from django.core.management import call_command

            with connection.cursor() as cursor:
                # Verificar que existan las tablas necesarias
                cursor.execute("""
                               SELECT name
                               FROM sqlite_master
                               WHERE type = 'table'
                                 AND name IN (
                                              'accounts_menucategory',
                                              'accounts_navigation',
                                              'auth_group'
                                   );
                               """)
                tables = [row[0] for row in cursor.fetchall()]

                # Solo ejecutar si todas las tablas existen
                if len(tables) >= 3:
                    print("🔧 Configurando estructura de menú automáticamente...")
                    call_command('setup_default_menu', verbosity=1)

        except Exception as e:
            # Si hay algún error (ej: durante migraciones), ignorar silenciosamente
            pass