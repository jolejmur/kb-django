# apps/sales_team_management/apps.py
from django.apps import AppConfig


class SalesTeamManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sales_team_management'
    verbose_name = 'Sales Team Management'

    def ready(self):
        """Se ejecuta cuando la app está lista"""
        try:
            # Importar signals si los hay
            # import apps.sales_team_management.signals
            pass
        except ImportError:
            pass