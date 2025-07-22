"""
Middleware de seguridad simplificado para prevenir ataques de fuerza bruta
"""
import time
from django.core.cache import cache
from django.shortcuts import render
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SimpleBruteForceMiddleware:
    """
    Middleware simplificado para protección contra fuerza bruta
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.MAX_ATTEMPTS = 5
        self.LOCKOUT_TIME = 900  # 15 minutos

    def __call__(self, request):
        # Solo aplicar a login POST
        if request.path == '/accounts/login/' and request.method == 'POST':
            client_ip = self.get_client_ip(request)
            
            # Verificar si está bloqueada
            if self.is_blocked(client_ip):
                logger.warning(f"IP bloqueada intentando login: {client_ip}")
                return render(request, 'security/blocked.html', {
                    'ip_address': client_ip,
                    'remaining_time': self.get_remaining_time(client_ip),
                    'lockout_minutes': self.LOCKOUT_TIME // 60
                }, status=429)
        
        response = self.get_response(request)
        
        # Registrar fallo si es login POST con status 200
        if (request.path == '/accounts/login/' and 
            request.method == 'POST' and 
            response.status_code == 200):
            
            client_ip = self.get_client_ip(request)
            self.register_failed_attempt(client_ip)
        
        return response

    def get_client_ip(self, request):
        """Obtener IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_blocked(self, ip):
        """Verificar si IP está bloqueada"""
        blocked_until = cache.get(f'blocked_ip:{ip}', 0)
        return time.time() < blocked_until

    def register_failed_attempt(self, ip):
        """Registrar intento fallido"""
        key = f'failed_attempts:{ip}'
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, 300)  # 5 minutos
        
        if attempts >= self.MAX_ATTEMPTS:
            # Bloquear IP
            blocked_until = time.time() + self.LOCKOUT_TIME
            cache.set(f'blocked_ip:{ip}', blocked_until, self.LOCKOUT_TIME)
            logger.error(f"IP {ip} bloqueada por {attempts} intentos fallidos")

    def get_remaining_time(self, ip):
        """Tiempo restante de bloqueo"""
        blocked_until = cache.get(f'blocked_ip:{ip}', 0)
        return max(0, int(blocked_until - time.time()))


class SimpleSecurityHeaders:
    """Headers de seguridad básicos"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers básicos de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY' 
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response