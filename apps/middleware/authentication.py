from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.conf import settings

class AuthenticationMiddleware:
    """
    Middleware to handle authentication redirections.

    If a user is not authenticated and tries to access any URL other than login,
    they will be redirected to the login page.

    If a user is authenticated and tries to access the login page,
    they will be redirected to their dashboard.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip this middleware for static and media files
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL):
            return self.get_response(request)

        # Try to resolve the URL to check if it's valid
        try:
            resolve(request.path)
        except Resolver404:
            # If URL is not valid and user is not authenticated, redirect to login
            if not request.user.is_authenticated:
                return redirect('accounts:login')

        # If user is authenticated and tries to access login page, redirect to dashboard
        if request.user.is_authenticated and request.path == reverse('accounts:login'):
            return redirect('dashboard:profile')

        # If user is not authenticated and tries to access any page other than login,
        # redirect to login page
        if not request.user.is_authenticated and request.path != reverse('accounts:login'):
            # Define public paths that don't require authentication
            public_paths = [
                '/admin/',
                '/marketing/webhook/',
                '/sales/public/',
                '/sales/ajax/generate-username',
                '/sales/ajax/toggle-public-registration'
            ]
            
            # Check if current path starts with any public path
            is_public_path = any(request.path.startswith(path) for path in public_paths)
            
            if not is_public_path:
                return redirect('accounts:login')

        response = self.get_response(request)
        return response