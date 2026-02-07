"""
Authentication views: Login, Logout
"""
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.username}!")
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Login yoki parol noto'g'ri")
    
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, "Tizimdan chiqdingiz")
    return redirect('login')


@login_required
def profile_view(request):
    """User profile view."""
    return render(request, 'accounts/profile.html')
