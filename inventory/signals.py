"""
Signals for automatic Stock creation when Product is created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, Stock


@receiver(post_save, sender=Product)
def create_stock_for_product(sender, instance, created, **kwargs):
    """Auto-create Stock record when a new Product is created."""
    if created:
        Stock.objects.get_or_create(product=instance, defaults={'current_qty': 0})
