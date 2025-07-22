# apps/accounts/urls.py - ACTUALIZAR LAS RUTAS DE CATEGORÍAS

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # === MÓDULOS (GROUPS) ===
    path('admin/modules/', views.modules_list, name='modules_list'),
    path('admin/modules/create/', views.module_create, name='module_create'),
    path('admin/modules/<int:pk>/edit/', views.module_edit, name='module_edit'),
    path('admin/modules/<int:pk>/delete/', views.module_delete, name='module_delete'),
    path('admin/modules/<int:pk>/', views.module_detail, name='module_detail'),

    # === CATEGORÍAS DEL MENÚ - VERSIÓN AVANZADA ===
    path('admin/categories/', views.categories_list, name='categories_list'),
    path('admin/categories/create/', views.category_create, name='category_create'),
    path('admin/categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('admin/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('admin/categories/<int:pk>/', views.category_detail, name='category_detail'),

    # === NAVEGACIÓN ===
    path('admin/navigation/', views.navigation_list, name='navigation_list'),
    path('admin/navigation/create/', views.navigation_create, name='navigation_create'),
    path('admin/navigation/<int:pk>/edit/', views.navigation_edit, name='navigation_edit'),
    path('admin/navigation/<int:pk>/delete/', views.navigation_delete, name='navigation_delete'),
    path('admin/navigation/<int:pk>/', views.navigation_detail, name='navigation_detail'),

    # === ROLES ===
    path('roles/', views.roles_list, name='roles_list'),
    path('admin/roles/', views.roles_list, name='admin_roles_list'),
    path('admin/roles/create/', views.role_create, name='role_create'),
    path('admin/roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('admin/roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    path('admin/roles/<int:pk>/', views.role_detail, name='role_detail'),

    # === USUARIOS ===
    path('users/', views.users_list, name='users_list'),
    path('admin/users/', views.users_list, name='admin_users_list'),
    path('admin/users/create/', views.user_create, name='user_create'),
    path('admin/users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('admin/users/<int:pk>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('admin/users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('admin/users/<int:pk>/', views.user_detail, name='user_detail'),

    # === GRUPOS DE TRABAJO ===
    path('groups/', views.modules_list, name='groups_list'),

    # === ASIGNACIÓN DE MÓDULOS A ROLES ===
    path('admin/role-assignments/', views.role_assignments, name='role_assignments'),
    path('admin/role-assignments/<int:role_id>/', views.role_assignment_detail, name='role_assignment_detail'),
]