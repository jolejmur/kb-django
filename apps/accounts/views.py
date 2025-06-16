from django.shortcuts import redirect
from django.contrib.auth import logout

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