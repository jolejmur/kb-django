# config/settings/base.py - ACTUALIZACIÓN DE INSTALLED_APPS

# Agregar esta línea a INSTALLED_APPS:

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Local apps
    'apps.core',
    'apps.accounts',
    'apps.dashboard',
    'apps.sales_team_management',  # ← NUEVA APP AGREGADA
]

# También agregar en config/urls.py:

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def redirect_to_dashboard(request):
    """Redirect root URL to dashboard if authenticated, otherwise to login"""
    if request.user.is_authenticated:
        return redirect('dashboard:profile')
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', redirect_to_dashboard, name='home'),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('sales/', include('apps.sales_team_management.urls')),  # ← NUEVA URL AGREGADA
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)