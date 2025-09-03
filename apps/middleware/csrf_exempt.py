"""
Middleware para excluir rutas específicas de la verificación CSRF
"""

class CSRFExemptMiddleware:
    """
    Middleware que excluye ciertas rutas de la verificación CSRF
    Debe colocarse ANTES de CsrfViewMiddleware en MIDDLEWARE
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Rutas que deben estar exentas de CSRF
        self.exempt_paths = [
            '/sales/public/register/submit/',
            '/sales/ajax/generate-username/',
        ]
    
    def __call__(self, request):
        # Si la ruta está en la lista de exentas, marcar el request como exempt
        if any(request.path.startswith(path) for path in self.exempt_paths):
            setattr(request, '_dont_enforce_csrf_checks', True)
        
        response = self.get_response(request)
        return response