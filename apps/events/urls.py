from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Gestión de eventos
    path('', views.eventos_list, name='eventos_list'),
    path('create/', views.evento_create, name='evento_create'),
    path('<int:pk>/', views.evento_detail, name='evento_detail'),
    path('<int:pk>/edit/', views.evento_edit, name='evento_edit'),
    path('<int:pk>/delete/', views.evento_delete, name='evento_delete'),
    
    # Gestión de invitaciones QR
    path('<int:evento_id>/invitations/', views.invitaciones_list, name='invitaciones_list'),
    path('<int:evento_id>/generate-qr/', views.generar_qr, name='generar_qr'),
    path('invitation/<uuid:codigo_qr>/download/', views.descargar_qr, name='descargar_qr'),
    
    # Escaneo de QR y registro de visitas
    path('scan/<uuid:codigo_qr>/', views.scan_qr, name='scan_qr'),
    path('info/<uuid:codigo_qr>/', views.qr_info, name='qr_info'),
    path('public/<uuid:codigo_qr>/', views.public_qr_info, name='public_qr_info'),
    path('test-public/<uuid:codigo_qr>/', views.test_public_view, name='test_public'),
    path('register-visit/', views.registrar_visita, name='registrar_visita'),
    
    # Reportes y estadísticas
    path('<int:evento_id>/reports/', views.evento_reports, name='evento_reports'),
    path('<int:evento_id>/reports/export/', views.export_visitas, name='export_visitas'),
    
    # AJAX endpoints
    path('ajax/validate-qr/', views.ajax_validate_qr, name='ajax_validate_qr'),
    path('ajax/search-client/', views.ajax_search_client, name='ajax_search_client'),
    
    # API para el perfil del usuario
    path('api/user-qrs/', views.user_qr_codes, name='user_qr_codes'),
    
    # Módulo de escáner para personal de recepción
    path('scanner/', views.scanner_dashboard, name='scanner_dashboard'),
    path('scanner/scan/', views.scanner_scan, name='scanner_scan'),
]