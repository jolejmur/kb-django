from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from .models import User

@login_required
def profile(request):
    """
    View for displaying user profile.
    """
    user = request.user

    context = {
        'user': user,
        'title': 'Profile',
    }

    return render(request, 'accounts/profile.html', context)

@login_required
def edit_profile(request):
    """
    View for editing user profile.
    """
    user = request.user

    if request.method == 'POST':
        # This is a simplified version, in a real app you would use a form
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']

        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')

    context = {
        'user': user,
        'title': 'Edit Profile',
    }

    return render(request, 'accounts/edit_profile.html', context)

def custom_logout(request):
    """
    Custom logout view that explicitly destroys the session and redirects to the login page.
    """
    # Logout the user
    logout(request)

    # Explicitly clear session data
    request.session.flush()

    # Redirect to login page
    return redirect('accounts:login')
