from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import CoreSettings

def index(request):
    """
    Home page view.
    """
    settings = CoreSettings.get_settings()
    
    context = {
        'settings': settings,
        'title': 'Home',
    }
    
    return render(request, 'core/index.html', context)

@login_required
def dashboard(request):
    """
    Dashboard view, requires login.
    """
    settings = CoreSettings.get_settings()
    
    context = {
        'settings': settings,
        'title': 'Dashboard',
    }
    
    return render(request, 'core/dashboard.html', context)