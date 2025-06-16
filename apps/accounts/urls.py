from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # === MÓDULOS ===
    path('admin/modules/', views.modules_list, name='modules_list'),
    path('admin/modules/create/', views.module_create, name='module_create'),
    path('admin/modules/<int:pk>/edit/', views.module_edit, name='module_edit'),
    path('admin/modules/<int:pk>/delete/', views.module_delete, name='module_delete'),
    path('admin/modules/<int:pk>/', views.module_detail, name='module_detail'),

    # === ROLES ===
    path('admin/roles/', views.roles_list, name='roles_list'),
    path('admin/roles/create/', views.role_create, name='role_create'),
    path('admin/roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('admin/roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    path('admin/roles/<int:pk>/', views.role_detail, name='role_detail'),

    # === USUARIOS ===
    path('admin/users/', views.users_list, name='users_list'),
    path('admin/users/create/', views.user_create, name='user_create'),
    path('admin/users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('admin/users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('admin/users/<int:pk>/', views.user_detail, name='user_detail'),
]