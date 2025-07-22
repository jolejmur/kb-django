"""
Middleware de seguridad mejorado para bloquear efectivamente ataques de fuerza bruta
"""
import time
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EffectiveBruteForceMiddleware:
    """
    Middleware que efectivamente bloquea ataques de fuerza bruta
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Configuraciones
        self.MAX_ATTEMPTS = getattr(settings, 'BRUTE_FORCE_MAX_ATTEMPTS', 5)
        self.LOCKOUT_TIME = getattr(settings, 'BRUTE_FORCE_LOCKOUT_TIME', 900)  # 15 minutos

    def __call__(self, request):
        # Solo aplicar a login POST
        if request.path == '/accounts/login/' and request.method == 'POST':
            client_ip = self.get_client_ip(request)
            
            # PRIMERO: Verificar si está bloqueada ANTES de procesar
            if self.is_blocked(client_ip):
                logger.warning(f"🚫 BLOQUEADO: IP {client_ip} intentando acceso")
                return self.render_blocked_response(request, client_ip)
        
        # Continuar con request normal
        response = self.get_response(request)
        
        # SOLO después de la respuesta, verificar si fue intento fallido
        if request.path == '/accounts/login/' and request.method == 'POST':
            client_ip = self.get_client_ip(request)
            
            # Si fue login exitoso (redirección), limpiar intentos
            if response.status_code in [302, 301]:
                self.clear_attempts(client_ip)
                logger.info(f"✅ Login exitoso: IP {client_ip} - intentos limpiados")
            
            # Si fue login fallido (200 con página de error), registrar
            elif response.status_code == 200 and self.is_failed_login_response(response):
                self.register_attempt(client_ip)
                
                # Verificar si debe ser bloqueada después del intento
                if self.should_block(client_ip):
                    self.block_ip(client_ip)
                    logger.error(f"🔒 IP BLOQUEADA: {client_ip} alcanzó límite de intentos")
        
        return response

    def get_client_ip(self, request):
        """Obtener IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    def is_blocked(self, ip):
        """Verificar si IP está bloqueada"""
        blocked_until = cache.get(f'blocked_ip:{ip}')
        if blocked_until:
            return time.time() < blocked_until
        return False

    def register_attempt(self, ip):
        """Registrar cada intento de login"""
        key = f'login_attempts:{ip}'
        attempts = cache.get(key, 0) + 1
        
        # Guardar por 15 minutos
        cache.set(key, attempts, 900)
        
        logger.warning(f"⚠️  Intento #{attempts} desde IP: {ip}")
        return attempts

    def should_block(self, ip):
        """Verificar si debe bloquear después del intento actual"""
        attempts = cache.get(f'login_attempts:{ip}', 0)
        return attempts >= self.MAX_ATTEMPTS

    def block_ip(self, ip):
        """Bloquear IP inmediatamente"""
        blocked_until = time.time() + self.LOCKOUT_TIME
        cache.set(f'blocked_ip:{ip}', blocked_until, self.LOCKOUT_TIME)
        
        # También limpiar contador de intentos
        cache.delete(f'login_attempts:{ip}')
        
        logger.error(f"🔒 IP BLOQUEADA: {ip} por {self.LOCKOUT_TIME//60} minutos")

    def clear_attempts(self, ip):
        """Limpiar intentos de una IP"""
        cache.delete(f'login_attempts:{ip}')
        cache.delete(f'blocked_ip:{ip}')
    
    def is_failed_login_response(self, response):
        """Detectar si la respuesta indica login fallido"""
        try:
            if hasattr(response, 'content'):
                content_str = response.content.decode('utf-8', errors='ignore').lower()
                # Buscar indicadores de error en español
                error_indicators = [
                    'usuario o contraseña incorrectos',
                    'credenciales incorrectas', 
                    'error',
                    'invalid',
                    'incorrect',
                    'wrong'
                ]
                return any(indicator in content_str for indicator in error_indicators)
        except:
            pass
        return False

    def render_blocked_response(self, request, ip):
        """Respuesta para IP bloqueada"""
        remaining = self.get_remaining_time(ip)
        
        return HttpResponse(
            f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>IP Bloqueada</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>🚫 Acceso Bloqueado</h1>
                <p><strong>Su IP ({ip}) ha sido bloqueada temporalmente.</strong></p>
                <p>Demasiados intentos de login fallidos.</p>
                <p>Tiempo restante: <strong>{remaining//60} minutos, {remaining%60} segundos</strong></p>
                <p>Inténtelo de nuevo más tarde.</p>
            </body>
            </html>
            """,
            status=429
        )

    def get_remaining_time(self, ip):
        """Tiempo restante de bloqueo"""
        blocked_until = cache.get(f'blocked_ip:{ip}', 0)
        if blocked_until:
            remaining = int(blocked_until - time.time())
            return max(0, remaining)
        return 0


class SecurityHeadersMiddleware:
    """Headers de seguridad"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers básicos de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response