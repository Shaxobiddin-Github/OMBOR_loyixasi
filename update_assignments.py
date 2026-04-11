import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from inventory.models import Employee, Category


def assign_categories():
    """Xodimlarga toifalar biriktirish va Komandir tayinlash."""

    # ── Kategoriyalarni olish ──
    elektronika = Category.objects.get(name='Elektronika')
    maishiy     = Category.objects.get(name='Maishiy texnika')
    mebel       = Category.objects.get(name='Mebel')
    kiyim       = Category.objects.get(name='Kiyim-kechak')
    oziq        = Category.objects.get(name='Oziq-ovqat')

    # ── Ali Valiyev → KOMANDIR, Elektronika + Mebel ──
    ali = Employee.objects.get(employee_id='EMP001')
    ali.is_commander = True
    ali.assigned_categories.set([elektronika, mebel])
    ali.save()
    print(f"{ali.name} → KOMANDIR | Toifalar: Elektronika, Mebel")

    # ── Vali Aliyev → Kiyim-kechak, Oziq-ovqat ──
    vali = Employee.objects.get(employee_id='EMP002')
    vali.assigned_categories.set([kiyim, oziq])
    vali.save()
    print(f"{vali.name} → Toifalar: Kiyim-kechak, Oziq-ovqat")

    # ── Gani Teshayev → Maishiy texnika ──
    gani = Employee.objects.get(employee_id='EMP003')
    gani.assigned_categories.set([maishiy])
    gani.save()
    print(f"{gani.name} → Toifalar: Maishiy texnika")


if __name__ == '__main__':
    assign_categories()
    print("\nToifalar muvaffaqiyatli biriktirildi!")
