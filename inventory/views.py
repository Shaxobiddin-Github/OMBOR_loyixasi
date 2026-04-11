"""
Inventory views for warehouse management.
- Dashboard
- Movement IN/OUT with Face ID verification
- Product list with pagination and QR lookup
- Face verification endpoint
- Backup download
"""
import json
import os
import glob
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from django.conf import settings
from django.contrib import messages

from accounts.decorators import admin_required, operator_required
from .models import Employee, Category, Product, Stock, Movement, MovementItem
from .services import StockService, CheckoutService
from .face_service import FaceService


# ============================================
# Face Verification Session Helpers
# ============================================

def check_face_verified(request):
    """
    Check if face verification is still valid.
    Returns employee_id if valid, None otherwise.
    
    Validates:
    - Session has face verification data
    - Same user who verified
    - Same station/IP
    - Within timeout period
    """
    verified_at_str = request.session.get('face_verified_at')
    if not verified_at_str:
        return None
    
    # Parse with timezone awareness
    verified_at = parse_datetime(verified_at_str)
    if verified_at is None:
        return None
    
    if timezone.is_naive(verified_at):
        verified_at = timezone.make_aware(verified_at)
    
    # Check timeout
    elapsed = (timezone.now() - verified_at).total_seconds()
    if elapsed > settings.FACE_VERIFICATION_TIMEOUT:
        return None
    
    # Security: same user who verified
    if request.session.get('face_verified_user_id') != request.user.id:
        return None
    
    # Security: same station/IP
    current_station = request.META.get('REMOTE_ADDR', '')
    if request.session.get('face_verified_station') != current_station:
        return None
    
    return request.session.get('face_verified_employee_id')


def clear_face_session(request):
    """Clear face verification data from session."""
    keys = [
        'face_verified_employee_id',
        'face_verified_user_id', 
        'face_verified_station',
        'face_verified_at',
        'face_confidence'
    ]
    for key in keys:
        request.session.pop(key, None)


# ============================================
# Dashboard
# ============================================

@login_required
def dashboard(request):
    """Main dashboard with statistics."""
    # Get counts
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_employees = Employee.objects.filter(is_active=True).count()
    
    # Stock summary
    stocks = Stock.objects.select_related('product').all()
    low_stock_count = sum(1 for s in stocks if s.is_low_stock)
    
    # Recent movements
    recent_movements = Movement.objects.select_related(
        'performed_by', 'face_employee'
    ).order_by('-created_at')[:10]
    
    # Today's movements
    today = timezone.now().date()
    today_in = Movement.objects.filter(
        movement_type='IN', 
        status='VERIFIED',
        created_at__date=today
    ).count()
    today_out = Movement.objects.filter(
        movement_type='OUT', 
        status='VERIFIED',
        created_at__date=today
    ).count()
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_employees': total_employees,
        'low_stock_count': low_stock_count,
        'recent_movements': recent_movements,
        'today_in': today_in,
        'today_out': today_out,
    }
    return render(request, 'inventory/dashboard.html', context)


# ============================================
# Face Verification Endpoints
# ============================================

@login_required
@require_POST
def face_verify(request):
    """
    POST /inventory/face/verify/
    Body: {"image": "base64..."}
    
    Stores verification in session with user_id and station.
    Returns: {"ok": bool, "employee_id": int, "name": str, "confidence": float}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    image_b64 = data.get('image', '')
    if not image_b64:
        return JsonResponse({'ok': False, 'error': 'Rasm berilmadi'}, status=400)
    
    # Convert base64 to frame
    frame = FaceService.base64_to_frame(image_b64)
    if frame is None:
        return JsonResponse({'ok': False, 'error': 'Rasmni o\'qib bo\'lmadi'}, status=400)
    
    # Verify face
    service = FaceService()
    result = service.verify_face(frame)
    
    if result['success']:
        try:
            employee = Employee.objects.get(face_label=result['face_label'])
        except Employee.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Xodim topilmadi'})
        
        # Store in session with security info
        request.session['face_verified_employee_id'] = employee.id
        request.session['face_verified_user_id'] = request.user.id
        request.session['face_verified_station'] = request.META.get('REMOTE_ADDR', '')
        request.session['face_verified_at'] = timezone.now().isoformat()
        request.session['face_confidence'] = result['confidence']
        
        categories = list(employee.assigned_categories.values('id', 'name'))
        
        return JsonResponse({
            'ok': True,
            'employee_id': employee.id,
            'name': employee.name,
            'confidence': result['confidence'],
            'is_commander': employee.is_commander,
            'categories': categories,
        })
    
    return JsonResponse({'ok': False, 'error': result['message']})


@login_required
@require_GET
def face_status(request):
    """Check current face verification status with category/commander info."""
    employee_id = check_face_verified(request)
    if employee_id:
        try:
            employee = Employee.objects.get(id=employee_id)
            categories = list(employee.assigned_categories.values('id', 'name'))
            return JsonResponse({
                'verified': True,
                'employee_id': employee.id,
                'name': employee.name,
                'confidence': request.session.get('face_confidence', 0),
                'is_commander': employee.is_commander,
                'categories': categories,
            })
        except Employee.DoesNotExist:
            pass
    
    return JsonResponse({'verified': False})


@login_required
@admin_required
@require_POST
def face_register(request, employee_id):
    """
    POST /inventory/face/register/<employee_id>/
    Body: {"images": ["base64...", "base64...", ...]}
    
    Register employee face with 10-30 images.
    """
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Xodim topilmadi'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    images_b64 = data.get('images', [])
    if not images_b64 or len(images_b64) < 10:
        return JsonResponse({
            'ok': False, 
            'error': f'Kamida 10 ta rasm kerak ({len(images_b64)} berildi)'
        }, status=400)
    
    # Convert base64 to frames
    frames = []
    for img_b64 in images_b64:
        frame = FaceService.base64_to_frame(img_b64)
        if frame is not None:
            frames.append(frame)
    
    if len(frames) < 10:
        return JsonResponse({
            'ok': False,
            'error': f'Kamida 10 ta yuz kerak ({len(frames)} o\'qildi)'
        }, status=400)
    
    # Register face
    service = FaceService()
    result = service.register_employee(employee.face_label, frames)
    
    return JsonResponse({
        'ok': result['success'],
        'faces_count': result['faces_count'],
        'message': result['message']
    })


# ============================================
# Product Endpoints
# ============================================

@login_required
@require_GET
def product_by_barcode(request):
    """
    GET /inventory/product/by-barcode/?q=...
    
    Returns product info with current stock.
    Supports Barcode, SKU, and Name search.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'found': False, 'error': 'Kod berilmadi'})
    
    try:
        # Try exact/insensitive match on Barcode first (most common)
        product = Product.objects.filter(barcode__iexact=query).first()
        
        # If not found, try SKU
        if not product:
            product = Product.objects.filter(sku__iexact=query).first()
            
        # If still not found, try Name (only if query is long enough to avoid bad matches)
        if not product and len(query) > 3:
            product = Product.objects.filter(name__icontains=query).first()
            
        if not product:
             return JsonResponse({'found': False, 'error': f'Mahsulot topilmadi: {query}'})

        # Get stock info
        stock = Stock.objects.filter(product=product).first()
        
        return JsonResponse({
            'found': True,
            'product': {
                'id': product.id,
                'uid': str(product.uid),
                'name': product.name,
                'sku': product.sku,
                'barcode': product.barcode,
                'unit': product.unit,
                'category': product.category.name,
                'assigned_to': {
                    'id': product.assigned_to.id,
                    'name': product.assigned_to.name
                } if product.assigned_to else None,
                'stock_qty': stock.current_qty if stock else 0,
                'min_stock': product.min_stock
            }
        })
    except Exception as e:
        return JsonResponse({'found': False, 'error': str(e)})


@login_required
def product_list(request):
    """Paginated product list with search."""
    search = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    
    products = Product.objects.select_related('category', 'stock').all()
    
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(barcode__icontains=search)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    products = products.order_by('name')
    
    paginator = Paginator(products, settings.DEFAULT_PAGE_SIZE)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    
    categories = Category.objects.all()
    
    context = {
        'products': products_page,
        'categories': categories,
        'search': search,
        'selected_category': category_id,
    }
    return render(request, 'inventory/product_list.html', context)


# ============================================
# Movement Views
# ============================================

@login_required
@operator_required
def movement_in(request):
    """Kirim (IN) movement page."""
    # Check for pending movement
    pending = Movement.objects.filter(
        performed_by=request.user,
        movement_type='IN',
        status='PENDING'
    ).first()

    # Auto-cleanup old pending movements (older than 24 hours)
    if pending and pending.created_at < timezone.now() - timedelta(hours=24):
        pending.status = 'CANCELLED'
        pending.save()
        pending = None
    
    # Serialize pending items
    pending_items = []
    if pending:
        for item in pending.items.select_related('product', 'product__stock').all():
            pending_items.append({
                'id': item.id,
                'productId': item.product.id,
                'name': item.product.name,
                'sku': item.product.sku,
                'quantity': item.quantity,
                'unit': item.product.unit,
                'stockQty': getattr(item.product.stock, 'current_qty', 0) if hasattr(item.product, 'stock') else 0
            })

    # Serialize employees based on Face ID verification
    # If Face ID is verified:
    # - Commander: sees self + subordinates
    # - Regular: sees only self
    # If NOT verified:
    # - Show ALL active employees (user must verify face to proceed properly)
    
    actor_id = check_face_verified(request)
    employees = Employee.objects.filter(is_active=True).prefetch_related('assigned_categories')

    if actor_id:
        try:
            actor = Employee.objects.get(id=actor_id)
            if actor.is_commander:
                # Commander: Self + Subordinates
                employees = employees.filter(Q(id=actor.id) | Q(supervisor=actor))
            else:
                # Regular: Only Self
                employees = employees.filter(id=actor.id)
        except Employee.DoesNotExist:
            pass # Should not happen if session is valid

    employees_data = []
    for emp in employees:
        cats = list(emp.assigned_categories.values('id', 'name'))
        employees_data.append({
            'id': emp.id,
            'name': emp.name,
            'employee_id': emp.employee_id,
            'is_commander': emp.is_commander,
            'supervisor_id': emp.supervisor_id,
            'categories': cats,
        })

    context = {
        'movement_type': 'IN',
        'movement_type_display': 'Kirim',
        'pending_movement': pending,
        'pending_items_json': json.dumps(pending_items),
        'employees': employees,
        'employees_json': json.dumps(employees_data),
        'face_verified': actor_id is not None,
        'user_employee_id': request.user.employee.id if hasattr(request.user, 'employee') else None,
    }
    return render(request, 'inventory/movement_form.html', context)


@login_required
@operator_required
def movement_out(request):
    """Chiqim (OUT) checkout page — toifa asosidagi."""
    # Check for pending movement
    pending = Movement.objects.filter(
        performed_by=request.user,
        movement_type='OUT',
        status='PENDING'
    ).first()

    # Auto-cleanup old pending movements
    if pending and pending.created_at < timezone.now() - timedelta(hours=24):
        pending.status = 'CANCELLED'
        pending.save()
        pending = None

    # Serialize pending items
    pending_items = []
    if pending:
        for item in pending.items.select_related('product', 'product__stock').all():
            pending_items.append({
                'id': item.id,
                'productId': item.product.id,
                'name': item.product.name,
                'sku': item.product.sku,
                'quantity': item.quantity,
                'unit': item.product.unit,
                'stockQty': getattr(item.product.stock, 'current_qty', 0) if hasattr(item.product, 'stock') else 0
            })
            
    employees = Employee.objects.filter(is_active=True).prefetch_related('assigned_categories')
    employees_data = []
    for emp in employees:
        cats = list(emp.assigned_categories.values('id', 'name'))
        employees_data.append({
            'id': emp.id,
            'name': emp.name,
            'employee_id': emp.employee_id,
            'is_commander': emp.is_commander,
            'supervisor_id': emp.supervisor_id,
            'categories': cats,
        })
    
    context = {
        'movement_type': 'OUT',
        'movement_type_display': 'Chiqim',
        'pending_movement': pending,
        'pending_items_json': json.dumps(pending_items),
        'face_verified': check_face_verified(request) is not None,
        'employees': employees,
        'employees_json': json.dumps(employees_data),
        'user_employee_id': request.user.employee.id if hasattr(request.user, 'employee') else None,
    }
    return render(request, 'inventory/checkout_form.html', context)


@login_required
@operator_required
@require_POST
def create_movement(request):
    """
    Create a new PENDING movement.
    POST body: {"movement_type": "IN"|"OUT", "note": "..."}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    movement_type = data.get('movement_type', '').upper()
    if movement_type not in ['IN', 'OUT']:
        return JsonResponse({'ok': False, 'error': 'Noto\'g\'ri harakat turi'}, status=400)
    
    # Cancel any existing pending movement of same type
    # This acts as a 'force restart' if a pending movement already exists
    Movement.objects.filter(
        performed_by=request.user,
        movement_type=movement_type,
        status='PENDING'
    ).update(status='CANCELLED')
    
    movement = Movement.objects.create(
        movement_type=movement_type,
        status='PENDING',
        performed_by=request.user,
        note=data.get('note', ''),
        target_employee_id=data.get('target_employee_id')
    )
    
    return JsonResponse({
        'ok': True,
        'movement_id': movement.id
    })


@login_required
@operator_required
@require_POST
def add_movement_item(request, movement_id):
    """
    Add item to PENDING movement.
    POST body: {"product_id": int, "quantity": int, "unit_price": float}
    """
    try:
        movement = Movement.objects.get(
            id=movement_id,
            performed_by=request.user,
            status='PENDING'
        )
    except Movement.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Movement topilmadi'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    # ... (existing code)
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 0))
    unit_price = float(data.get('unit_price', 0))
    target_id = data.get('target_employee_id')

    if quantity <= 0:
        return JsonResponse({'ok': False, 'error': 'Miqdor 0 dan katta bo\'lishi kerak'}, status=400)

    # Allow updating target_employee if movement is empty
    if target_id and not movement.items.exists():
        try:
            target_emp = Employee.objects.get(id=target_id)
            movement.target_employee = target_emp
            movement.save()
        except Employee.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Tanlangan xodim topilmadi'}, status=400)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Mahsulot topilmadi'}, status=404)
    # ...
    
    # Check stock for OUT (optional warning)
    warning = None
    if movement.movement_type == 'OUT':
        stock = Stock.objects.filter(product=product).first()
        stock_qty = stock.current_qty if stock else 0
        if stock_qty < quantity:
            warning = f'Diqqat: Zaxira yetarli emas (mavjud: {stock_qty}). Qoldiq minusga o\'tadi.'
    
    # 5. Ownership & Permission Check for IN (Strict via Face ID)
    if movement.movement_type == 'IN':
        # MANDATORY: Verify Actor via Face ID
        actor_id = check_face_verified(request)
        if not actor_id:
            return JsonResponse({
                'ok': False, 
                'error': 'Face ID orqali shaxsingizni tasdiqlang.'
            }, status=403)
            
        try:
            actor = Employee.objects.get(id=actor_id)
        except Employee.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Tasdiqlangan xodim topilmadi.'}, status=403)

        # Product Owner
        product_owner = product.assigned_to
        
        # If product has no owner, anyone can claim it? 
        # Or maybe it must be assigned first? 
        # Let's assume if no owner, the Actor claims it (sets target to Self).
        if not product_owner:
            # If target not set, defaults to Actor
            if not movement.target_employee:
                movement.target_employee = actor
                movement.save()
            # If target is set, Actor must have permission for that Target
            # (Logic handled below under "Permission to act for Target")
        
        else:
            # Product has owner. 
            # 1. Target must match Owner (You can only "IN" items into Owner's stock)
            if not movement.target_employee:
                 movement.target_employee = product_owner
                 movement.save()
            elif movement.target_employee != product_owner:
                return JsonResponse({
                    'ok': False,
                    'error': f'Bu mahsulot {product_owner.name} ga tegishli. Uni {movement.target_employee.name} nomiga kirim qilib bo\'lmaydi.'
                }, status=400)
        
        
        # Permission Check: Can ACTOR perform action for TARGET?
        # Target is now guaranteed to be set (either product_owner or Actor)
        target = movement.target_employee
        
        logger = logging.getLogger(__name__)
        logger.debug(f"Permission: Actor={actor.id}(cmd={actor.is_commander}), Target={target.id}(sup={target.supervisor_id})")

        is_allowed = False
        if actor.id == target.id:
            is_allowed = True
        elif actor.is_commander and target.supervisor_id == actor.id:
            is_allowed = True
            
        if not is_allowed:
            return JsonResponse({
                'ok': False,
                'error': f'Sizda {target.name} uchun kirim qilish huquqi yo\'q.'
            }, status=403)


    # Create or update item
    item, created = MovementItem.objects.get_or_create(
        movement=movement,
        product=product,
        defaults={'quantity': quantity, 'unit_price': unit_price}
    )
    
    if not created:
        item.quantity += quantity
        item.unit_price = unit_price
        item.save()
    
    return JsonResponse({
        'ok': True,
        'item_id': item.id,
        'total_quantity': item.quantity,
        'warning': warning
    })


@login_required
@operator_required
@require_POST
def remove_movement_item(request, movement_id, item_id):
    """Remove item from PENDING movement."""
    try:
        movement = Movement.objects.get(
            id=movement_id,
            performed_by=request.user,
            status='PENDING'
        )
    except Movement.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Movement topilmadi'}, status=404)
    
    try:
        item = MovementItem.objects.get(id=item_id, movement=movement)
        item.delete()
        return JsonResponse({'ok': True})
    except MovementItem.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Element topilmadi'}, status=404)


@login_required
@operator_required
@require_POST
def finalize_movement(request, movement_id):
    """
    Finalize PENDING movement. Face verification required.
    """
    try:
        movement = Movement.objects.get(
            id=movement_id,
            performed_by=request.user,
            status='PENDING'
        )
    except Movement.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Movement topilmadi'}, status=404)
    
    # Check items exist
    if not movement.items.exists():
        return JsonResponse({'ok': False, 'error': 'Harakat bo\'sh - mahsulot qo\'shing'}, status=400)
    
    # FACE ID MANDATORY CHECK
    employee_id = check_face_verified(request)
    if not employee_id:
        return JsonResponse({
            'ok': False, 
            'error': 'Face ID tasdiqlanmagan yoki muddati o\'tgan. Qayta tasdiqlang.'
        }, status=403)
    
    confidence = request.session.get('face_confidence', 0)
    
    try:
        StockService.process_movement(movement, employee_id, confidence)
        clear_face_session(request)
        return JsonResponse({'ok': True, 'message': 'Harakat muvaffaqiyatli yakunlandi'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@operator_required
@require_POST
def cancel_movement(request, movement_id):
    """Cancel PENDING movement."""
    try:
        movement = Movement.objects.get(
            id=movement_id,
            performed_by=request.user,
            status='PENDING'
        )
        movement.status = 'CANCELLED'
        movement.save()
        return JsonResponse({'ok': True})
    except Movement.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Movement topilmadi'}, status=404)


@login_required
def movement_list(request):
    """Movement history with filtering."""
    movement_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    
    movements = Movement.objects.select_related(
        'performed_by', 'face_employee'
    ).prefetch_related('items__product')
    
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    if status:
        movements = movements.filter(status=status)
    
    movements = movements.order_by('-created_at')
    
    paginator = Paginator(movements, settings.DEFAULT_PAGE_SIZE)
    page = request.GET.get('page', 1)
    movements_page = paginator.get_page(page)
    
    context = {
        'movements': movements_page,
        'selected_type': movement_type,
        'selected_status': status,
    }
    return render(request, 'inventory/movement_list.html', context)


@login_required
def movement_detail(request, movement_id):
    """Movement detail with items."""
    movement = get_object_or_404(
        Movement.objects.select_related('performed_by', 'face_employee')
        .prefetch_related('items__product'),
        id=movement_id
    )
    
    context = {
        'movement': movement,
        'can_reverse': (
            request.user.role == 'admin' and 
            movement.status == 'VERIFIED' and
            not Movement.objects.filter(reversed_movement=movement).exists()
        )
    }
    return render(request, 'inventory/movement_detail.html', context)


@login_required
@admin_required
@require_POST
def reverse_movement(request, movement_id):
    """
    Create reversal for a VERIFIED movement. Admin only.
    POST body: {"reason": "..."}
    """
    try:
        movement = Movement.objects.get(id=movement_id)
    except Movement.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Movement topilmadi'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}
    
    reason = data.get('reason', 'Sabab ko\'rsatilmagan')
    
    try:
        reversal = StockService.reverse_movement(movement, request.user, reason)
        return JsonResponse({
            'ok': True,
            'reversal_id': reversal.id,
            'message': 'Harakat bekor qilindi'
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@operator_required
@require_POST
def discard_pending_movement(request):
    """
    Forcefully discard (cancel) PENDING movements of a specific type.
    Redirects back to the movement page.
    POST data: movement_type (IN/OUT)
    """
    movement_type = request.POST.get('movement_type', '').upper()
    if movement_type in ['IN', 'OUT']:
        Movement.objects.filter(
            performed_by=request.user,
            movement_type=movement_type,
            status='PENDING'
        ).update(status='CANCELLED')
        
    if movement_type == 'IN':
        return redirect('movement_in')
    elif movement_type == 'OUT':
        return redirect('movement_out')
    return redirect('dashboard')


@login_required
@operator_required
@require_POST
def bulk_out_all_stock(request):
    """
    POST /movement/bulk-out/
    Create a PENDING OUT movement with ALL products that have stock > 0.
    Each item's quantity = current stock level.
    After Face ID + finalize, all stock goes to 0.
    """
    # Get all stocks with qty > 0
    stocks_with_qty = Stock.objects.select_related('product').filter(current_qty__gt=0)

    if not stocks_with_qty.exists():
        return JsonResponse({
            'ok': False,
            'error': 'Omborda chiqarish uchun mahsulot yo\'q (barcha zaxira 0)'
        }, status=400)

    # Cancel any existing pending OUT movements for this user
    Movement.objects.filter(
        performed_by=request.user,
        movement_type='OUT',
        status='PENDING'
    ).update(status='CANCELLED')

    # Create new PENDING OUT movement
    movement = Movement.objects.create(
        movement_type='OUT',
        status='PENDING',
        performed_by=request.user,
        note='Barcha mahsulotlarni chiqarish (bulk out)'
    )

    # Create MovementItem for each product with stock
    items_data = []
    for stock in stocks_with_qty:
        item = MovementItem.objects.create(
            movement=movement,
            product=stock.product,
            quantity=stock.current_qty,
            unit_price=0
        )
        items_data.append({
            'id': item.id,
            'productId': stock.product.id,
            'name': stock.product.name,
            'sku': stock.product.sku,
            'quantity': stock.current_qty,
            'unit': stock.product.unit,
            'stockQty': stock.current_qty,
        })

    return JsonResponse({
        'ok': True,
        'movement_id': movement.id,
        'items': items_data,
        'total_products': len(items_data),
        'message': f'{len(items_data)} ta mahsulot chiqim uchun tayyor'
    })

# ============================================
# Checkout Endpoints (Category-based)
# ============================================

@login_required
@operator_required
@require_POST
def checkout_standard(request):
    """
    POST /checkout/standard/
    Body: {"product_id": int, "quantity": int, "target_employee_id": int (optional)}
    """
    # 1. Face verification
    employee_id = check_face_verified(request)
    if not employee_id:
        return JsonResponse({'ok': False, 'error': 'Face ID tasdiqlanmagan'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    manual_target_id = data.get('target_employee_id')
    
    if not product_id:
        return JsonResponse({'ok': False, 'error': 'product_id majburiy'}, status=400)
    if quantity <= 0:
        return JsonResponse({'ok': False, 'error': 'Miqdor musbat bo\'lishi kerak'}, status=400)

    # 2. Get Actor
    try:
        actor = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Xodim topilmadi'}, status=404)

    # 3. Get Product (Need owner to infer target)
    try:
        product = Product.objects.select_related('category', 'assigned_to').get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Mahsulot topilmadi'}, status=404)

    # 4. DETERMINE TARGET (Smart Logic)
    target = None
    
    if manual_target_id:
        # A. Manual Override
        try:
            target = Employee.objects.get(id=manual_target_id)
        except Employee.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Tanlangan xodim topilmadi'}, status=400)
    else:
        # B. Auto-Inference
        if not product.assigned_to:
            # Unowned -> Self-Scan (Claims for Actor)
            target = actor
        elif product.assigned_to.id == actor.id:
            # Owned by Actor -> Self-Scan
            target = actor
        else:
            # Owned by someone else. Check relation.
            owner = product.assigned_to
            if actor.is_commander and owner.supervisor_id == actor.id:
                # Owned by Subordinate -> Target = Owner
                target = owner
            else:
                # Owned by non-subordinate -> BLOCK
                return JsonResponse({
                    'ok': False,
                    'error': f"Mahsulot egasi ({owner.name}) sizning qo'l ostingizda emas."
                }, status=403)

    # Debug log
    print(f"DEBUG: checkout_standard | Product: {product.id} | Owner: {product.assigned_to_id if product.assigned_to else 'None'} | Target: {target.id} | Actor: {actor.id}")

    # 5. Permission Check (Actor vs Target)
    try:
        CheckoutService._resolve_permission(actor, target)
    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=403)

    # 6. Ownership Validation (Double Check)
    # If target is NOT the product owner, and product HAS an owner, block it.
    # Exception: If product has NO owner, we allow target (usually Actor) to take it.
    if product.assigned_to and product.assigned_to.id != target.id:
         return JsonResponse({
            'ok': False, 
            'error': f"Bu mahsulot {target.name} ga tegishli emas. (Egasi: {product.assigned_to.name})"
        }, status=400)

    # 7. Get/Create PENDING Movement
    movement, created = Movement.objects.get_or_create(
        performed_by=request.user,
        movement_type='OUT',
        status='PENDING',
        defaults={
            'face_employee': actor,
            'target_employee': target,
            'face_verified': False,
            'created_at': timezone.now()
        }
    )

    # 8. Session Consistency Check
    if not created:
        if movement.target_employee and movement.target_employee.id != target.id:
            if movement.items.exists():
                return JsonResponse({
                    'ok': False, 
                    'error': f"Joriy sessiya {movement.target_employee.name} uchun ochilgan. Yakunlang yoki bekor qiling."
                }, status=400)
            else:
                # Empty session -> switch target
                movement.target_employee = target
                movement.save()
        elif not movement.target_employee:
             movement.target_employee = target
             movement.save()

    # 9. Add Item
    item, item_created = MovementItem.objects.get_or_create(
        movement=movement,
        product=product,
        defaults={'quantity': 0}
    )
    item.quantity += quantity
    item.save()

    # Check stock warning
    stock_qty = getattr(product.stock, 'current_qty', 0) if hasattr(product, 'stock') else 0
    warning = None
    if stock_qty < item.quantity:
        warning = f"Diqqat: Zaxira yetarli emas ({stock_qty}). Minusga o'tadi."

    # 10. Return Response (Include Target Info)
    items_data = list(movement.items.select_related('product').values(
        'id', 'product__name', 'product__sku', 'quantity'
    ))
    
    return JsonResponse({
        'ok': True,
        'movement_id': movement.id,
        'items': items_data,
        'message': f"{product.name} qo'shildi",
        'warning': warning,
        'target_id': target.id,
        'target_name': target.name
    })


@login_required
@operator_required
@require_POST
def checkout_emergency(request):
    """
    POST /checkout/emergency/
    Body: {"target_employee_id": int (optional)}
    """
    employee_id = check_face_verified(request)
    if not employee_id:
        return JsonResponse({'ok': False, 'error': 'Face ID tasdiqlanmagan'}, status=403)
        
    try:
        data = json.loads(request.body)
        target_id = data.get('target_employee_id')
    except:
        target_id = None

    try:
        actor = Employee.objects.get(id=employee_id)
        target = Employee.objects.get(id=target_id) if target_id else actor
    except Employee.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Xodim topilmadi'}, status=404)

    # Permission check
    try:
        CheckoutService._resolve_permission(actor, target)
    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=403)

    # Get/Create Movement
    movement, _ = Movement.objects.get_or_create(
        performed_by=request.user,
        movement_type='OUT',
        status='PENDING',
        defaults={
            'face_employee': actor,
            'target_employee': target,
            'face_verified': False,
            'created_at': timezone.now(),
            'is_emergency': True
        }
    )
    
    if movement.items.exists():
         # If existing items, ensure target matches or it's empty
         if movement.target_employee and movement.target_employee.id != target.id:
             return JsonResponse({'ok': False, 'error': 'Sessiya boshqa xodim uchun band. Yakunlang.'}, status=400)
    
    movement.target_employee = target
    movement.is_emergency = True
    movement.note = f"EKSTRENNIY: {target.name} (Items added)"
    movement.save()

    # Find all stock with qty > 0 assigned to target
    stocks = Stock.objects.filter(
        product__assigned_to=target, 
        current_qty__gt=0
    ).select_related('product')
    
    if not stocks.exists():
        return JsonResponse({'ok': False, 'error': 'Chiqarish uchun mahsulot qolmadi.'}, status=400)

    count = 0
    for s in stocks:
        item, _ = MovementItem.objects.get_or_create(
            movement=movement,
            product=s.product,
            defaults={'quantity': 0}
        )
        item.quantity = s.current_qty # Snap to current stock
        item.save()
        count += 1

    items_data = list(movement.items.select_related('product').values(
        'id', 'product__name', 'product__sku', 'quantity'
    ))

    return JsonResponse({
        'ok': True, 
        'movement_id': movement.id,
        'items': items_data,
        'message': f"{count} xil mahsulot qo'shildi. Yakunlashni bosing."
    })


# ============================================
# Backup
# ============================================

@login_required
@admin_required
def backup_download(request):
    """Download latest backup file."""
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    
    if not os.path.exists(backup_dir):
        messages.error(request, 'Backup papkasi mavjud emas')
        return redirect('dashboard')
    
    backups = sorted(glob.glob(os.path.join(backup_dir, '*.sql')), reverse=True)
    
    if not backups:
        messages.error(request, 'Backup fayli topilmadi')
        return redirect('dashboard')
    
    latest_backup = backups[0]
    return FileResponse(
        open(latest_backup, 'rb'),
        as_attachment=True,
        filename=os.path.basename(latest_backup)
    )


# ============================================
# Employee Management
# ============================================

@login_required
@admin_required
def employee_list(request):
    """Employee list."""
    employees = Employee.objects.all().order_by('name')
    
    context = {
        'employees': employees,
        'face_service': FaceService(),
    }
    return render(request, 'inventory/employee_list.html', context)


@login_required
@admin_required
def employee_detail(request, employee_id):
    """Employee detail with face registration."""
    employee = get_object_or_404(Employee, id=employee_id)
    
    context = {
        'employee': employee,
    }
    return render(request, 'inventory/employee_detail.html', context)


# ============================================
# Reports
# ============================================

@login_required
def report_dashboard(request):
    """Report dashboard with filters."""
    from datetime import datetime, timedelta
    
    # Default date range: last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    context = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    return render(request, 'inventory/report_dashboard.html', context)


@login_required
def download_stock_report(request):
    """Download current stock report (Excel or PDF)."""
    from django.http import HttpResponse
    from .reports import ReportService
    
    format_type = request.GET.get('format', 'excel')
    service = ReportService()
    
    data = service.get_stock_report_data()
    
    if format_type == 'pdf':
        context = {
            'stocks': data['stocks'],
            'total_items': data['total_items'],
            'total_qty': data['total_qty'],
            'generated_at': timezone.now(),
            'title': 'Ombor Qoldig\'i Hisoboti'
        }
        pdf_output = service.generate_pdf('inventory/reports/stock_pdf.html', context)
        if pdf_output:
            response = HttpResponse(pdf_output.read(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="stock_report.pdf"'
            return response
        return HttpResponse("PDF yaratishda xatolik", status=500)
    else:
        # Excel
        headers = ['ID', 'SKU', 'Shtrix kod (QR)', 'Nomi', 'Kategoriya', 'O\'lchov', 'Hozirgi Soni', 'Min Soni', 'Holat']
        excel_output = service.generate_excel(
            data['excel_data'], headers, 
            sheet_name="Ombor", title="Ombor Qoldig'i Hisoboti"
        )
        response = HttpResponse(
            excel_output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="stock_report.xlsx"'
        return response


@login_required 
def download_movement_report(request):
    """Download movement report (Excel or PDF)."""
    from django.http import HttpResponse
    from datetime import datetime
    from .reports import ReportService
    
    format_type = request.GET.get('format', 'excel')
    movement_type = request.GET.get('type', 'ALL')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.now().replace(day=1)
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else datetime.now()
        # Set end_date to end of day
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        return HttpResponse("Noto'g'ri sana formati", status=400)
    
    service = ReportService()
    data = service.get_movement_report_data(start_date, end_date, movement_type)
    
    type_label = {'IN': 'Kirim', 'OUT': 'Chiqim', 'ALL': 'Barcha'}.get(movement_type, 'Barcha')
    title = f"{type_label} Hisoboti ({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')})"
    
    if format_type == 'pdf':
        context = {
            'movements': data['movements'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'generated_at': timezone.now(),
            'title': title,
            'type_label': type_label
        }
        pdf_output = service.generate_pdf('inventory/reports/movement_pdf.html', context)
        if pdf_output:
            response = HttpResponse(pdf_output.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{movement_type.lower()}_report.pdf"'
            return response
        return HttpResponse("PDF yaratishda xatolik", status=500)
    else:
        # Excel
        headers = ['ID', 'Turi', 'Sana', 'Foydalanuvchi', 'Xodim (Face ID)', 'Mahsulotlar', 'Izoh']
        excel_output = service.generate_excel(
            data['excel_data'], headers,
            sheet_name="Harakatlar", title=title
        )
        response = HttpResponse(
            excel_output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{movement_type.lower()}_report.xlsx"'
        return response


@login_required
def download_low_stock_report(request):
    """Download low stock warning report."""
    from django.http import HttpResponse
    from django.db import models
    from .reports import ReportService
    
    format_type = request.GET.get('format', 'excel')
    
    # Get stocks where current_qty <= min_stock
    low_stocks = Stock.objects.select_related('product', 'product__category').filter(
        current_qty__lte=models.F('product__min_stock')
    ).annotate(
        deficit=models.F('product__min_stock') - models.F('current_qty')
    ).order_by('current_qty')
    
    excel_data = []
    for s in low_stocks:
        excel_data.append([
            s.product.id,
            s.product.sku,
            s.product.barcode,
            s.product.name,
            s.product.category.name,
            s.current_qty,
            s.product.min_stock,
            s.product.min_stock - s.current_qty  # Deficit
        ])
    
    service = ReportService()
    
    if format_type == 'pdf':
        context = {
            'stocks': low_stocks,
            'generated_at': timezone.now(),
            'title': 'Kamomat Hisoboti (Low Stock)'
        }
        pdf_output = service.generate_pdf('inventory/reports/low_stock_pdf.html', context)
        if pdf_output:
            response = HttpResponse(pdf_output.read(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="low_stock_report.pdf"'
            return response
        return HttpResponse("PDF yaratishda xatolik", status=500)
    else:
        headers = ['ID', 'SKU', 'Shtrix kod (QR)', 'Nomi', 'Kategoriya', 'Hozirgi Soni', 'Min Soni', 'Yetishmayotgan']
        excel_output = service.generate_excel(
            excel_data, headers,
            sheet_name="Kamomat", title="Kamomat Hisoboti"
        )
        response = HttpResponse(
            excel_output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="low_stock_report.xlsx"'
        return response


# ============================================
# QR Code Generation
# ============================================

@login_required
def qr_code_dashboard(request):
    """QR Code generation dashboard - list all products with QR codes."""
    from .qr_service import QRCodeService
    
    # Get all categories for filter dropdown
    categories = Category.objects.order_by('name')
    
    # Filter by category if specified
    category_id = request.GET.get('category')
    products = Product.objects.select_related('category').order_by('category__name', 'name')
    
    selected_category = None
    if category_id:
        try:
            selected_category = int(category_id)
            products = products.filter(category_id=category_id)
        except (ValueError, TypeError):
            pass
    
    # Generate QR codes for each product
    products_with_qr = []
    for product in products:
        qr_data = product.barcode or str(product.uid)
        qr_base64 = QRCodeService.generate_qr_base64(qr_data, size=150)
        products_with_qr.append({
            'product': product,
            'qr_base64': qr_base64,
            'qr_data': qr_data
        })
    
    context = {
        'products_with_qr': products_with_qr,
        'categories': categories,
        'selected_category': selected_category,
    }
    return render(request, 'inventory/qr_dashboard.html', context)


@login_required
def qr_code_single(request, product_id):
    """Generate QR code image for a single product."""
    from .qr_service import QRCodeService
    
    product = get_object_or_404(Product, id=product_id)
    qr_data = product.barcode or str(product.uid)
    
    return QRCodeService.generate_qr_response(qr_data, filename=f"qr_{product.sku}.png")


@login_required
def qr_code_print(request):
    """Printable page with selected products' QR codes."""
    from .qr_service import QRCodeService
    
    # Get selected product IDs from query params
    product_ids = request.GET.getlist('ids')
    
    if product_ids:
        products = Product.objects.filter(id__in=product_ids).select_related('category')
    else:
        # If no IDs specified, get all products
        products = Product.objects.select_related('category').order_by('name')[:50]
    
    products_with_qr = []
    for product in products:
        qr_data = product.barcode or str(product.uid)
        qr_base64 = QRCodeService.generate_qr_base64(qr_data, size=200)
        products_with_qr.append({
            'product': product,
            'qr_base64': qr_base64,
            'qr_data': qr_data
        })
    
    context = {
        'products_with_qr': products_with_qr,
    }
    return render(request, 'inventory/qr_print.html', context)


