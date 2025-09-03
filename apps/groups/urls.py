from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    # Dashboard principal de reportes
    path('', views.reports_dashboard, name='reports_dashboard'),
    
    # Reportes específicos
    path('reportes/asignacion-leads/', views.lead_assignment_report, name='lead_assignment_report'),
]