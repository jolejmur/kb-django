"""
Middleware de seguridad para prevenir ataques de fuerza bruta
"""
import time
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class BruteForceProtectionMiddleware:
    """
    Middleware para proteger contra ataques de fuerza bruta
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Configuraciones (pueden ser sobreescritas en settings)
        self.MAX_ATTEMPTS = getattr(settings, 'BRUTE_FORCE_MAX_ATTEMPTS', 5)
        self.LOCKOUT_TIME = getattr(settings, 'BRUTE_FORCE_LOCKOUT_TIME', 300)  # 5 minutos
        self.ATTEMPT_WINDOW = getattr(settings, 'BRUTE_FORCE_ATTEMPT_WINDOW', 300)  # 5 minutos

    def __call__(self, request):
        # Solo aplicar a login
        if request.path == '/accounts/login/' and request.method == 'POST':
            client_ip = self.get_client_ip(request)
            
            # Verificar si la IP está bloqueada
            if self.is_blocked(client_ip):
                logger.warning(f"Intento de login bloqueado desde IP: {client_ip}")
                return self.render_blocked_response(request, client_ip)
            
            # Continuar con la request
            response = self.get_response(request)
            
            # Si es login fallido (200 pero con errores), registrar intento
            if response.status_code == 200 and self.is_failed_login(request, response):
                self.register_failed_attempt(client_ip)
                logger.warning(f"Intento de login fallido desde IP: {client_ip}")
            
            # Si es login exitoso, limpiar intentos
            elif response.status_code in [302, 301]:  # Redirección = login exitoso
                self.clear_failed_attempts(client_ip)
                logger.info(f"Login exitoso desde IP: {client_ip}")
            
            return response
        
        return self.get_response(request)

    def get_client_ip(self, request):
        """Obtener la IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_blocked(self, ip):
        """Verificar si una IP está bloqueada"""
        blocked_until = cache.get(f'blocked_ip:{ip}')
        if blocked_until and time.time() < blocked_until:
            return True
        return False

    def register_failed_attempt(self, ip):
        """Registrar un intento fallido"""
        key = f'failed_attempts:{ip}'
        attempts = cache.get(key, [])
        current_time = time.time()
        
        # Limpiar intentos antiguos (fuera de la ventana de tiempo)
        attempts = [t for t in attempts if current_time - t < self.ATTEMPT_WINDOW]
        
        # Agregar nuevo intento
        attempts.append(current_time)
        
        # Guardar en cache
        cache.set(key, attempts, self.ATTEMPT_WINDOW)
        
        # Si excede el límite, bloquear IP
        if len(attempts) >= self.MAX_ATTEMPTS:
            self.block_ip(ip)

    def block_ip(self, ip):
        """Bloquear una IP por tiempo determinado"""
        blocked_until = time.time() + self.LOCKOUT_TIME
        cache.set(f'blocked_ip:{ip}', blocked_until, self.LOCKOUT_TIME)
        logger.error(f"IP bloqueada por ataques de fuerza bruta: {ip}")

    def clear_failed_attempts(self, ip):
        """Limpiar intentos fallidos de una IP"""
        cache.delete(f'failed_attempts:{ip}')

    def is_failed_login(self, request, response):
        """Detectar si fue un login fallido"""
        # Si la respuesta es 200 (no redirección), probablemente es fallo
        # En login exitoso Django suele redireccionar (302/301)
        if response.status_code == 200:
            # Verificar si el contenido incluye indicadores de error
            try:
                if hasattr(response, 'content'):
                    content_str = response.content.decode('utf-8', errors='ignore').lower()
                    error_indicators = ['error', 'invalid', 'incorrect', 'wrong', 'fail']
                    return any(indicator in content_str for indicator in error_indicators)
            except:
                pass
        return False

    def render_blocked_response(self, request, ip):
        """Renderizar respuesta de IP bloqueada"""
        remaining_time = self.get_remaining_lockout_time(ip)
        context = {
            'ip_address': ip,
            'remaining_time': remaining_time,
            'lockout_minutes': self.LOCKOUT_TIME // 60
        }
        
        return render(
            request, 
            'security/blocked.html', 
            context, 
            status=429
        )

    def get_remaining_lockout_time(self, ip):
        """Obtener tiempo restante de bloqueo"""
        blocked_until = cache.get(f'blocked_ip:{ip}')
        if blocked_until:
            remaining = int(blocked_until - time.time())
            return max(0, remaining)
        return 0


class SecurityHeadersMiddleware:
    """
    Middleware para agregar headers de seguridad
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response