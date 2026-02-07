"""
Role-based access control decorators.
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def admin_required(view_func):
    """Decorator: Only admin role can access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'admin':
            return HttpResponseForbidden("Faqat admin uchun ruxsat berilgan")
        return view_func(request, *args, **kwargs)
    return wrapper


def operator_required(view_func):
    """Decorator: Admin or Operator can access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role not in ['admin', 'operator']:
            return HttpResponseForbidden("Faqat operator yoki admin uchun ruxsat berilgan")
        return view_func(request, *args, **kwargs)
    return wrapper


def viewer_required(view_func):
    """Decorator: Any authenticated user can access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
