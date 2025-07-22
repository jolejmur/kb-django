# apps/sales_team_management/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard principal
    path('', views.sales_dashboard, name='dashboard'),

    # ============================================================
    # URLs PARA GESTIÓN DE COMISIONES
    # ============================================================
    path('comisiones/', views.comisiones_equipos_list, name='comisiones_equipos'),
    path('comisiones/proyectos/', views.comisiones_proyectos_list, name='comisiones_proyectos'),

    # ============================================================
    # URLs PARA EQUIPOS DE VENTA
    # ============================================================
    path('equipos/', views.equipos_venta_list, name='equipos_list'),
    path('equipos/crear/', views.equipos_venta_create, name='equipos_create'),
    path('equipos/<int:pk>/', views.equipos_venta_detail, name='equipos_detail'),
    path('equipos/<int:pk>/editar/', views.equipos_venta_edit, name='equipos_edit'),
    path('equipos/<int:pk>/eliminar/', views.equipos_venta_delete, name='equipos_delete'),
    
    # Jerarquía de equipos (vista separada)
    path('jerarquia/', views.jerarquia_equipos_list, name='jerarquia_list'),
    path('jerarquia/crear/', views.jerarquia_create_member, name='jerarquia_create_member'),
    path('jerarquia/<int:member_id>/<str:rol>/ver/', views.jerarquia_member_detail, name='jerarquia_member_detail'),
    path('jerarquia/<int:member_id>/<str:rol>/editar/', views.jerarquia_member_edit, name='jerarquia_member_edit'),
    path('jerarquia/<int:member_id>/<str:rol>/eliminar/', views.jerarquia_member_delete, name='jerarquia_member_delete'),
    path('jerarquia/<int:member_id>/<str:rol>/reasignar/', views.jerarquia_member_reassign, name='jerarquia_member_reassign'),
    path('jerarquia/<int:member_id>/<str:rol>/inactivar/', views.jerarquia_member_deactivate, name='jerarquia_member_deactivate'),
    path('jerarquia/<int:member_id>/<str:rol>/toggle-estado/', views.jerarquia_member_toggle_status, name='jerarquia_member_toggle_status'),

    # Gestión de jerarquía de equipos
    path('equipos/<int:pk>/jerarquia/', views.equipos_manage_hierarchy, name='equipos_hierarchy'),
    path('equipos/<int:pk>/agregar-gerente/', views.equipos_add_gerente, name='equipos_add_gerente'),
    path('equipos/<int:pk>/agregar-miembro/', views.equipos_add_member, name='equipos_add_member'),

    # Comisiones de venta
    path('equipos/<int:equipo_pk>/comisiones/', views.comisiones_venta_config, name='comisiones_venta'),

    # ============================================================
    # URLs PARA PROYECTOS
    # ============================================================
    path('proyectos/', views.proyectos_list, name='proyectos_list'),
    path('proyectos/crear/', views.proyectos_create, name='proyectos_create'),
    path('proyectos/<int:pk>/', views.proyectos_detail, name='proyectos_detail'),
    path('proyectos/<int:pk>/editar/', views.proyectos_edit, name='proyectos_edit'),
    path('proyectos/<int:pk>/eliminar/', views.proyectos_delete, name='proyectos_delete'),

    # Comisiones de desarrollo
    path('proyectos/<int:proyecto_pk>/comisiones/', views.comisiones_desarrollo_config, name='comisiones_desarrollo'),

    # ============================================================
    # URLs PARA INMUEBLES
    # ============================================================
    path('proyectos/<int:proyecto_pk>/inmuebles/', views.inmuebles_list, name='inmuebles_list'),
    path('proyectos/<int:proyecto_pk>/inmuebles/crear/', views.inmuebles_create, name='inmuebles_create'),
    path('proyectos/<int:proyecto_pk>/inmuebles/<int:pk>/', views.inmuebles_detail, name='inmuebles_detail'),
    path('proyectos/<int:proyecto_pk>/inmuebles/<int:pk>/editar/', views.inmuebles_edit, name='inmuebles_edit'),
    path('proyectos/<int:proyecto_pk>/inmuebles/<int:pk>/eliminar/', views.inmuebles_delete, name='inmuebles_delete'),

    # ============================================================
    # APIs AJAX
    # ============================================================
    path('ajax/equipos/search/', views.ajax_equipos_search, name='ajax_equipos_search'),
    path('ajax/proyectos/search/', views.ajax_proyectos_search, name='ajax_proyectos_search'),
    path('ajax/proyectos/<int:proyecto_pk>/inmuebles/', views.ajax_inmuebles_by_proyecto,
         name='ajax_inmuebles_by_proyecto'),
    
    # Gestión de miembros AJAX
    path('ajax/miembros/cambiar-estado/', views.ajax_cambiar_estado_miembro, name='ajax_cambiar_estado_miembro'),
    path('ajax/miembros/migrar/', views.ajax_migrar_miembro, name='ajax_migrar_miembro'),
    path('ajax/miembros/verificar-subordinados/', views.ajax_verificar_subordinados, name='ajax_verificar_subordinados'),
    path('ajax/supervisores/', views.ajax_get_supervisores, name='ajax_get_supervisores'),
    
    # Búsqueda y creación de usuarios AJAX
    path('ajax/search-users/', views.ajax_search_users, name='ajax_search_users'),
    path('ajax/create-user/', views.ajax_create_user, name='ajax_create_user'),
]