"""
URL configuration for DjangoProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from apps.events.views import public_qr_info
from django.http import HttpResponse
from apps.events.models import InvitacionQR
from django.db import models

def qr_public_secure_view(request, codigo_qr):
    """Vista pública segura para qrkorban.duckdns.org - Sin middleware de autenticación"""
    import logging
    from django.utils import timezone
    
    # Log de acceso para seguridad
    logger = logging.getLogger('qr_access')
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    
    try:
        # Acceso controlado y seguro a la base de datos
        invitacion = InvitacionQR.objects.select_related('evento', 'vendedor').get(
            codigo_qr=codigo_qr,
            activa=True,  # Solo QR activos
            evento__activo=True,  # Solo eventos activos
            evento__fecha_fin__gt=timezone.now()  # Solo eventos no finalizados
        )
        
        # Log de acceso exitoso
        logger.info(f"QR_ACCESS_SUCCESS: {codigo_qr} from {client_ip} - {user_agent}")
        
        # Incrementar contador de vistas (seguro)
        user_agent_lower = user_agent.lower()
        is_bot = any(bot in user_agent_lower for bot in ['bot', 'crawl', 'spider', 'scraper'])
        
        if not is_bot:
            InvitacionQR.objects.filter(codigo_qr=codigo_qr).update(
                vistas_qr=models.F('vistas_qr') + 1
            )
        
        # Solo datos necesarios y seguros
        vendor_name = invitacion.vendedor.get_full_name() or invitacion.vendedor.username
        download_url = f"https://korban.duckdns.org/events/invitation/{codigo_qr}/download/"
        
        # HTML optimizado y seguro
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{invitacion.evento.nombre} - Invitación</title>
    <meta name="robots" content="noindex, nofollow">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            padding: 20px;
        }}
        .container {{ 
            max-width: 500px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 20px; 
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1); 
        }}
        .header {{ 
            background: linear-gradient(45deg, #6366f1, #8b5cf6); 
            color: white; 
            padding: 30px 20px; 
            text-align: center; 
        }}
        .icon {{ font-size: 40px; margin-bottom: 15px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header p {{ opacity: 0.9; }}
        .content {{ padding: 25px; }}
        .info-card {{ 
            background: #f8fafc; 
            border-left: 4px solid #8b5cf6; 
            padding: 15px; 
            margin: 15px 0; 
            border-radius: 8px; 
        }}
        .info-card h3 {{ color: #374151; margin-bottom: 8px; font-size: 16px; }}
        .info-card p {{ color: #6b7280; line-height: 1.5; }}
        .download-btn {{ 
            display: block; 
            width: 100%; 
            background: #8b5cf6; 
            color: white; 
            padding: 18px; 
            text-align: center; 
            text-decoration: none; 
            border-radius: 12px; 
            font-weight: 600; 
            font-size: 16px;
            margin: 25px 0; 
            transition: background-color 0.3s;
        }}
        .download-btn:hover {{ background: #7c3aed; }}
        .footer {{ 
            text-align: center; 
            color: #9ca3af; 
            font-size: 14px; 
            padding: 20px;
            border-top: 1px solid #e5e7eb;
        }}
        @media (max-width: 480px) {{
            .container {{ margin: 10px; border-radius: 15px; }}
            .header {{ padding: 25px 15px; }}
            .content {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="icon">🎪</div>
            <h1>{invitacion.evento.nombre}</h1>
            <p>¡Estás invitado al evento!</p>
        </div>
        
        <div class="content">
            <div class="info-card">
                <h3>📅 Fecha y Hora</h3>
                <p>{invitacion.evento.fecha_inicio.strftime('%A, %d de %B de %Y')}<br>
                {invitacion.evento.fecha_inicio.strftime('%H:%M')} hrs</p>
            </div>
            
            <div class="info-card">
                <h3>📍 Ubicación</h3>
                <p>{invitacion.evento.ubicacion}</p>
            </div>
            
            <div class="info-card">
                <h3>👤 Tu Agente Comercial</h3>
                <p>{vendor_name}</p>
            </div>
            
            <div class="info-card">
                <h3>📋 Instrucciones</h3>
                <p>• Llega puntual al evento<br>
                • Presenta este código QR al personal de recepción<br>
                • El personal registrará tu asistencia<br>
                • Tu agente comercial te atenderá en el evento</p>
            </div>
            
            <a href="{download_url}" class="download-btn" download="{invitacion.evento.nombre}_QR.png">
                📥 Descargar Código QR
            </a>
        </div>
        
        <div class="footer">
            Invitación generada por {vendor_name}<br>
            <small>Código: {str(codigo_qr)[:8]}...</small>
        </div>
    </div>
</body>
</html>"""
        
        return HttpResponse(html)
        
    except InvitacionQR.DoesNotExist:
        # Log de acceso fallido
        logger.warning(f"QR_ACCESS_FAILED: {codigo_qr} from {client_ip} - NOT_FOUND")
        
        return HttpResponse("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QR No Válido</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            background: #fee2e2; 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            padding: 20px;
        }}
        .error-container {{ 
            background: white; 
            padding: 40px; 
            border-radius: 20px; 
            text-align: center; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            max-width: 400px;
        }}
        .error-icon {{ font-size: 48px; margin-bottom: 20px; }}
        h1 {{ color: #dc2626; margin-bottom: 15px; }}
        p {{ color: #6b7280; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🚫</div>
        <h1>Código QR No Válido</h1>
        <p>El código QR no existe, ha expirado o el evento ya finalizó.</p>
        <p><small>Si crees que esto es un error, contacta con tu agente comercial.</small></p>
    </div>
</body>
</html>""", status=404)
    
    except Exception as e:
        # Log de error del sistema
        logger.error(f"QR_ACCESS_ERROR: {codigo_qr} from {client_ip} - {str(e)}")
        
        return HttpResponse("""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Error del Sistema</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>⚠️ Error Temporal</h1>
    <p>Ocurrió un error temporal. Por favor, intenta nuevamente en unos momentos.</p>
</body>
</html>""", status=500)

def test_public_simple(request, codigo_qr):
    """Vista de prueba super simple"""
    return HttpResponse(f"<h1>QR Test: {codigo_qr}</h1><p>NO LOGIN REQUIRED</p>")

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
    path('sales/', include('apps.sales_team_management.urls')),
    path('projects/', include('apps.real_estate_projects.urls')),
    path('marketing/', include('apps.whatsapp_business.urls')),
    path('events/', include('apps.events.urls')),
    path('leads/', include(('apps.whatsapp_business.urls', 'leads'))),
    
    # Vista pública para QR de eventos (sin middleware de autenticación)
    path('qr/<uuid:codigo_qr>/', public_qr_info, name='public_qr'),
    path('test/<uuid:codigo_qr>/', test_public_simple, name='test_simple'),
    
    # Vista segura para subdominio qrkorban.duckdns.org
    path('<uuid:codigo_qr>/', qr_public_secure_view, name='qr_public_secure'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)