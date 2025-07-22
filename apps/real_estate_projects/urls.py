# apps/real_estate_projects/urls.py
from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Dashboard de proyectos
    path('dashboard/', views.projects_dashboard, name='dashboard'),
    
    # Gestión de proyectos
    path('', views.proyectos_list, name='list'),
    path('crear/', views.proyectos_create, name='create'),
    path('<int:pk>/', views.proyectos_detail, name='detail'),
    path('<int:pk>/editar/', views.proyectos_edit, name='edit'),
    path('<int:pk>/eliminar/', views.proyectos_delete, name='delete'),
    
    # Gestión de fases
    path('<int:proyecto_pk>/fases/', views.fases_list, name='fases_list'),
    path('<int:proyecto_pk>/fases/crear/', views.fases_create, name='fases_create'),
    path('fases/<int:pk>/editar/', views.fase_edit, name='fase_edit'),
    path('fases/<int:pk>/eliminar/', views.fase_delete, name='fase_delete'),
    
    # Gestión de inmuebles
    path('inmuebles/', views.inmuebles_list, name='inmuebles_list'),
    path('<int:proyecto_pk>/inmuebles/', views.inmuebles_by_project, name='inmuebles_by_project'),
    path('inmuebles/crear/', views.inmueble_create, name='inmueble_create_general'),
    path('fases/<int:fase_pk>/inmuebles/crear/', views.inmueble_create, name='inmueble_create'),
    path('inmuebles/<int:pk>/', views.inmueble_detail, name='inmueble_detail'),
    path('inmuebles/<int:pk>/editar/', views.inmueble_edit, name='inmueble_edit'),
    path('inmuebles/<int:pk>/eliminar/', views.inmueble_delete, name='inmueble_delete'),
    
    # Roles management removed - now handled through project creation/editing
    
    # Gestión de ponderadores
    path('<int:proyecto_pk>/ponderadores/', views.ponderadores_list, name='ponderador_list'),
    path('<int:proyecto_pk>/ponderadores/crear/', views.ponderador_create, name='ponderador_create'),
    path('<int:proyecto_pk>/ponderadores/<int:pk>/', views.ponderador_detail, name='ponderador_detail'),
    path('<int:proyecto_pk>/ponderadores/<int:pk>/editar/', views.ponderador_edit, name='ponderador_edit'),
    path('<int:proyecto_pk>/ponderadores/<int:pk>/activar/', views.ponderador_activate, name='ponderador_activate'),
    path('<int:proyecto_pk>/ponderadores/<int:pk>/desactivar/', views.ponderador_deactivate, name='ponderador_deactivate'),
    
    # Gestión de comercialización
    path('<int:proyecto_pk>/fases/<int:fase_pk>/comercializacion/', views.fase_comercializacion, name='fase_comercializacion'),
    path('<int:proyecto_pk>/torres/<int:torre_pk>/comercializacion/', views.torre_comercializacion, name='torre_comercializacion'),
    path('<int:proyecto_pk>/sectores/<int:sector_pk>/comercializacion/', views.sector_comercializacion, name='sector_comercializacion'),
    
    # APIs AJAX
    path('ajax/proyectos/search/', views.ajax_proyectos_search, name='ajax_proyectos_search'),
    path('ajax/proyecto/<int:proyecto_pk>/tipo/', views.ajax_get_project_type, name='ajax_get_project_type'),
    path('ajax/fases/<int:proyecto_pk>/', views.ajax_fases_by_proyecto, name='ajax_fases_by_proyecto'),
    path('ajax/torres/<int:fase_pk>/', views.ajax_torres_by_fase, name='ajax_torres_by_fase'),
    path('ajax/pisos/<int:torre_pk>/', views.ajax_pisos_by_torre, name='ajax_pisos_by_torre'),
    path('ajax/sectores/<int:fase_pk>/', views.ajax_sectores_by_fase, name='ajax_sectores_by_fase'),
    path('ajax/manzanas/<int:sector_pk>/', views.ajax_manzanas_by_sector, name='ajax_manzanas_by_sector'),
    path('ajax/search-users/', views.ajax_search_users, name='ajax_search_users'),
    path('ajax/ponderador/crear/', views.ajax_create_ponderador, name='ajax_create_ponderador'),
]