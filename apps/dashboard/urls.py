from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Profile dashboard
    path('profile/', views.profile_dashboard, name='profile'),

    # Profile management
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
    
    # QR code download
    path('profile/qr-download/', views.download_qr_contact, name='download_qr'),
]