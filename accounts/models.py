"""
Custom User model with role-based access control.
Roles: Admin, Operator, Viewer
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with roles for warehouse access control."""
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('operator', 'Operator'),
        ('viewer', 'Viewer'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name="Rol"
    )
    
    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin_role(self):
        return self.role == 'admin'
    
    @property
    def is_operator_role(self):
        return self.role in ['admin', 'operator']
    
    @property
    def is_viewer_role(self):
        return True  # All roles can view
