# apps/sales_team_management/views.py

# This file has been refactored to improve maintainability.
# All views have been split into separate modules in the views/ directory.
# 
# The original views.py was 2977 lines long and has been split into:
# - views/dashboard.py - Dashboard and main sales views
# - views/helpers.py - Helper functions used across modules
# - views/equipos.py - Team management views
# - views/jerarquia.py - Team hierarchy management views  
# - views/proyectos.py - Project management views
# - views/inmuebles.py - Property management views
# - views/comisiones.py - Commission configuration views
# - views/ajax_views.py - AJAX endpoints for dynamic functionality
#
# All views are imported in views/__init__.py to maintain compatibility with urls.py

# Import all views to maintain compatibility with existing urls.py
from .views.dashboard import *
from .views.helpers import *
from .views.equipos import *
from .views.jerarquia import *
from .views.proyectos import *
from .views.inmuebles import *
from .views.comisiones import *
from .views.ajax_views import *





