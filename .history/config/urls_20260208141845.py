"""
URL configuration for Ombor Nazorat project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('inventory.urls')),
]

# ==============================================================================
# MUHIM QISM: Waitress (Service) orqali ishlaganda Dizayn buzilmasligi uchun
# Statik va Media fayllarni majburiy uzatish (Serve)
# ==============================================================================

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]