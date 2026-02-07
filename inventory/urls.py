"""
Inventory URL patterns.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Face verification
    path('face/verify/', views.face_verify, name='face_verify'),
    path('face/status/', views.face_status, name='face_status'),
    path('face/register/<int:employee_id>/', views.face_register, name='face_register'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('product/by-barcode/', views.product_by_barcode, name='product_by_barcode'),
    
    # Movements
    path('movement/in/', views.movement_in, name='movement_in'),
    path('movement/out/', views.movement_out, name='movement_out'),
    path('movement/create/', views.create_movement, name='create_movement'),
    path('movement/<int:movement_id>/add-item/', views.add_movement_item, name='add_movement_item'),
    path('movement/<int:movement_id>/remove-item/<int:item_id>/', views.remove_movement_item, name='remove_movement_item'),
    path('movement/<int:movement_id>/finalize/', views.finalize_movement, name='finalize_movement'),
    path('movement/<int:movement_id>/cancel/', views.cancel_movement, name='cancel_movement'),
    path('movement/discard/', views.discard_pending_movement, name='discard_pending_movement'),
    path('movement/<int:movement_id>/reverse/', views.reverse_movement, name='reverse_movement'),
    path('movements/', views.movement_list, name='movement_list'),
    path('movement/<int:movement_id>/', views.movement_detail, name='movement_detail'),
    
    # Employees
    path('employees/', views.employee_list, name='employee_list'),
    path('employee/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    
    # Backup
    path('backup/download/', views.backup_download, name='backup_download'),
    
    # Reports
    path('reports/', views.report_dashboard, name='report_dashboard'),
    path('reports/stock/', views.download_stock_report, name='download_stock_report'),
    path('reports/movement/', views.download_movement_report, name='download_movement_report'),
    path('reports/low-stock/', views.download_low_stock_report, name='download_low_stock_report'),
    
    # QR Codes
    path('qr-codes/', views.qr_code_dashboard, name='qr_code_dashboard'),
    path('qr-codes/product/<int:product_id>/', views.qr_code_single, name='qr_code_single'),
    path('qr-codes/print/', views.qr_code_print, name='qr_code_print'),
]
