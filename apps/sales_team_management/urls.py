# apps/sales_team_management/urls.py
from django.urls import path
from . import views

app_name = 'sales_team_management'

urlpatterns = [
    # ============================================================
    # DASHBOARD DE EQUIPOS - /sales/dashboard/
    # ============================================================
    path('dashboard/', views.sales_dashboard, name='dashboard'),

    # ============================================================
    # GESTIÓN DE EQUIPOS - /sales/team-management/
    # ============================================================
    path('team-management/', views.equipos_list, name='equipos_list'),
    path('team-management/create/', views.crear_equipo, name='crear_equipo'),
    path('team-management/<int:equipo_id>/detail/', views.equipo_detail, name='equipo_detail'),
    
    # Gestión de miembros
    path('team-management/<int:equipo_id>/add-member/', views.agregar_miembro, name='agregar_miembro'),
    path('team-management/members/<int:membership_id>/edit/', views.editar_miembro, name='editar_miembro'),
    path('team-management/members/<int:membership_id>/remove/', views.remover_miembro, name='remover_miembro'),

    # ============================================================
    # JERARQUÍA DE EQUIPOS - /sales/hierarchy/
    # ============================================================
    path('hierarchy/', views.jerarquia_list, name='jerarquia_list'),  # Vista con control de acceso automático
    path('hierarchy/assign/', views.asignar_supervisor, name='jerarquia_assign'),  # Nueva vista específica para asignación
    path('hierarchy/create/', views.crear_relacion_jerarquica, name='jerarquia_create'),
    path('hierarchy/<int:relation_id>/', views.jerarquia_detail, name='jerarquia_detail'),
    path('hierarchy/<int:relation_id>/edit/', views.editar_relacion_jerarquica, name='jerarquia_edit'),
    path('hierarchy/<int:relation_id>/toggle/', views.jerarquia_toggle, name='jerarquia_toggle'),
    path('hierarchy/<int:relation_id>/delete/', views.eliminar_relacion_jerarquica, name='jerarquia_delete'),
    path('hierarchy/analysis/', views.analisis_jerarquia, name='analisis_jerarquia'),
    
    # Jerarquía específica de equipos
    path('hierarchy/team/<int:equipo_id>/', views.jerarquia_equipo, name='jerarquia_equipo'),
    path('hierarchy/team/<int:equipo_id>/create/', views.crear_relacion_jerarquica_equipo, name='jerarquia_equipo_create'),

    # ============================================================
    # COMISIONES - /sales/commissions/
    # ============================================================
    path('commissions/', views.comisiones_equipos_list, name='comisiones_equipos_list'),
    path('commissions/projects/', views.comisiones_proyectos_list, name='comisiones_proyectos_list'),
    path('commissions/team/<int:unit_id>/', views.comisiones_equipo_config, name='comisiones_equipo_config'),
    path('commissions/structure/<int:structure_id>/', views.comision_structure_detail, name='comision_structure_detail'),
    path('commissions/development/<int:proyecto_pk>/', views.comisiones_desarrollo_config, name='comisiones_desarrollo_config'),

    # ============================================================
    # SUPERVISIÓN DIRECTA - /sales/supervision/
    # ============================================================
    path('supervision/', views.supervision_directa_list, name='supervision_directa_list'),
    path('supervision/create/', views.supervision_directa_create, name='supervision_directa_create'),
    path('supervision/<int:pk>/', views.supervision_directa_detail, name='supervision_directa_detail'),
    path('supervision/<int:pk>/edit/', views.supervision_directa_edit, name='supervision_directa_edit'),
    path('supervision/<int:pk>/toggle/', views.supervision_directa_toggle, name='supervision_directa_toggle'),
    path('supervision/<int:pk>/delete/', views.supervision_directa_delete, name='supervision_directa_delete'),

    # ============================================================
    # APIs AJAX
    # ============================================================
    path('ajax/teams/search/', views.ajax_equipos_search, name='ajax_equipos_search'),
    path('ajax/projects/search/', views.ajax_proyectos_search, name='ajax_proyectos_search'),
    path('ajax/projects/<int:proyecto_pk>/properties/', views.ajax_inmuebles_by_proyecto, name='ajax_inmuebles_by_proyecto'),
    
    # URLs AJAX legacy eliminadas - usar nuevo sistema de membresías
    
    # Búsqueda y creación de usuarios AJAX
    path('ajax/search-users/', views.ajax_search_users, name='ajax_search_users'),
    path('ajax/create-user/', views.ajax_create_user, name='ajax_create_user'),
    path('ajax/search-hierarchy/', views.ajax_search_hierarchy, name='ajax_search_hierarchy'),

    # AJAX para jerarquía y equipos
    path('ajax/hierarchy/<int:equipo_id>/', views.get_hierarchy_json, name='get_hierarchy_json'),
    path('ajax/supervisors/<int:membership_id>/', views.get_available_supervisors, name='get_available_supervisors'),
    path('ajax/team/<int:equipo_id>/members/', views.get_team_members_json, name='get_team_members_json'),
    path('ajax/team/<int:equipo_id>/positions/', views.get_available_positions, name='get_available_positions'),
    
    # AJAX para comisiones
    path('ajax/commissions/structure/<int:unit_id>/', views.get_commission_structure_json, name='get_commission_structure_json'),
    
    # AJAX para configuración de registro público
    path('ajax/toggle-public-registration/', views.ajax_toggle_public_registration, name='ajax_toggle_public_registration'),
    path('ajax/generate-username/', views.ajax_generate_username, name='ajax_generate_username'),
    
    # ============================================================
    # PERMISSION ERROR VIEWS
    # ============================================================
    path('permission-denied/', views.permission_denied_view, name='permission_denied'),
    
    # Redirect from old URLs
    path('', views.sales_dashboard, name='old_dashboard_redirect'),
    
    # ============================================================
    # PUBLIC REGISTRATION (Sin login requerido)
    # ============================================================
    path('public/register/submit/', views.public_register_submit, name='public_register_submit'),  # DEBE ir ANTES del patrón genérico
    path('public/success/<str:username>/', views.public_register_success, name='public_register_success'),
    path('public/register/<str:unit_code>/', views.public_register_form, name='public_register'),  # Patrón genérico al final
]