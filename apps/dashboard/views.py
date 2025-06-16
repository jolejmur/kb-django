from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from .forms import ProfileEditForm, CustomPasswordChangeForm


@login_required
def profile_dashboard(request):
    """
    Main profile dashboard view showing all user information.
    """
    user = request.user

    # Get user permissions
    permissions = user.get_permissions() if hasattr(user, 'get_permissions') else []

    # Get navigation items
    navigation_items = user.get_navigation_items() if hasattr(user, 'get_navigation_items') else []

    # Calculate account age
    account_age = timezone.now() - user.date_joined

    context = {
        'user': user,
        'permissions': permissions,
        'navigation_items': navigation_items,
        'account_age_days': account_age.days,
        'title': 'Profile Dashboard',
    }

    return render(request, 'pages/dashboard/profile.html', context)


@login_required
def edit_profile(request):
    """
    View for editing user profile information.
    """
    user = request.user

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('dashboard:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'title': 'Edit Profile',
    }

    return render(request, 'pages/dashboard/edit_profile.html', context)


@login_required
def change_password(request):
    """
    View for changing user password.
    """
    user = request.user

    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep user logged in
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('dashboard:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(user=user)

    context = {
        'form': form,
        'user': user,
        'title': 'Change Password',
    }

    return render(request, 'pages/dashboard/change_password.html', context)