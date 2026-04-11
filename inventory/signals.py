"""
Signals for automatic Stock creation when Product is created.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Stock, Employee
from .face_service import FaceService


@receiver(post_save, sender=Product)
def create_stock_for_product(sender, instance, created, **kwargs):
    """Auto-create Stock record when a new Product is created."""
    if created:
        Stock.objects.get_or_create(product=instance, defaults={'current_qty': 0})


@receiver(post_delete, sender=Employee)
def delete_employee_face_model(sender, instance, **kwargs):
    """Xodim o'chirilganda uning face model faylini ham o'chirish."""
    service = FaceService()
    service.delete_employee_model(instance.face_label)
