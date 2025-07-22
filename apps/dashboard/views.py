from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
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

    # Generate QR code with vCard contact info
    qr_data_url = None
    if user.get_full_name() and user.email:
        # Create vCard format
        vcard_data = f"""BEGIN:VCARD
VERSION:3.0
FN:{user.get_full_name()}
EMAIL:{user.email}
{'TEL:' + user.telefono if user.telefono else ''}
END:VCARD"""
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(vcard_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        qr_data_url = f"data:image/png;base64,{img_str}"

    context = {
        'user': user,
        'permissions': permissions,
        'navigation_items': navigation_items,
        'account_age_days': account_age.days,
        'qr_data_url': qr_data_url,
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


@login_required
def download_qr_contact(request):
    """
    Generate and download QR code as PNG image
    """
    user = request.user
    
    if not user.get_full_name() or not user.email:
        messages.error(request, 'Please complete your profile information first.')
        return redirect('dashboard:profile')
    
    # Create vCard format
    vcard_data = f"""BEGIN:VCARD
VERSION:3.0
FN:{user.get_full_name()}
EMAIL:{user.email}
{'TEL:' + user.telefono if user.telefono else ''}
END:VCARD"""
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=15,  # Larger for download
        border=4,
    )
    qr.add_data(vcard_data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Create HTTP response with image
    response = HttpResponse(content_type="image/png")
    response['Content-Disposition'] = f'attachment; filename="{user.get_full_name()}_contact.png"'
    img.save(response, format="PNG")
    
    return response