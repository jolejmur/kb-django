"""
Development settings for DjangoProject.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'korban.duckdns.org']

# CSRF trusted origins for HTTPS
CSRF_TRUSTED_ORIGINS = [
    'https://korban.duckdns.org',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Additional development apps
# INSTALLED_APPS += [
#     'django_extensions',  # Uncomment if you install django-extensions
# ]

# Django Debug Toolbar (uncomment if you install django-debug-toolbar)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'