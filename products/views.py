from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
import razorpay

from products.models import Coupon, Product


def _get_product_image_url(product):
    first_image = product.product_images.first()
    if first_image and first_image.image:
        return first_image.image.url
    if product.category and product.category.category_image:
        return product.category.category_image.url
    return ''


def _get_cart(request):
    return request.session.setdefault('cart', {})


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def _get_coupon(request):
    return request.session.get('coupon')


def _save_coupon(request, coupon):
    request.session['coupon'] = coupon
    request.session.modified = True


def _clear_coupon(request):
    request.session.pop('coupon', None)
    request.session.modified = True


def _set_coupon_error(request, message, code=''):
    request.session['coupon_error'] = message
    request.session['coupon_code_input'] = code
    request.session.modified = True


def _pop_coupon_feedback(request):
    coupon_error = request.session.pop('coupon_error', '')
    coupon_code_input = request.session.pop('coupon_code_input', '')
    request.session.modified = True
    return coupon_error, coupon_code_input


def _get_discount_amount(cart_total, coupon):
    if not coupon:
        return 0
    return min(cart_total, coupon['discount_price'])


def _get_available_coupons(cart_total):
    available_coupons = []

    for coupon in Coupon.objects.all().order_by('minimum_amount', 'Coupon_code'):
        if not coupon.is_valid():
            continue

        is_eligible = cart_total >= coupon.minimum_amount
        available_coupons.append({
            'code': coupon.Coupon_code,
            'discount_price': coupon.discount_price,
            'minimum_amount': coupon.minimum_amount,
            'is_eligible': is_eligible,
            'amount_needed': max(coupon.minimum_amount - cart_total, 0),
        })

    return available_coupons


def _get_cart_total(cart):
    return sum(item['unit_price'] * item['quantity'] for item in cart.values())


def get_product(request, slug):
    product = Product.objects.select_related('category').prefetch_related(
        'product_images',
        'size_variant',
    ).filter(slug=slug).first()

    if not product:
        return render(request, '404.html', status=404)

    context = {'product': product}

    size = request.GET.get('size')
    if size:
        context['selected_size'] = size
        context['updated_price'] = product.get_product_price_by_size(size)

    return render(request, 'product/product.html', context=context)


def add_to_cart(request, slug):
    product = Product.objects.select_related('category').prefetch_related(
        'product_images',
        'size_variant',
    ).filter(slug=slug).first()

    if not product:
        return render(request, '404.html', status=404)

    size = request.POST.get('size', '').strip()
    quantity = request.POST.get('quantity', '1').strip()

    try:
        quantity = max(1, int(quantity))
    except ValueError:
        quantity = 1

    if size and not product.size_variant.filter(size_name=size).exists():
        size = ''

    unit_price = product.get_product_price_by_size(size) if size else product.price
    item_key = f"{product.slug}__{size or 'default'}"

    cart = _get_cart(request)
    existing = cart.get(item_key)
    if existing:
        quantity += existing.get('quantity', 0)

    cart[item_key] = {
        'item_key': item_key,
        'slug': product.slug,
        'product_name': product.product_name,
        'quantity': quantity,
        'size': size,
        'unit_price': unit_price,
        'image_url': _get_product_image_url(product),
    }
    _save_cart(request, cart)

    messages.success(request, 'Item added to cart.')
    return redirect('cart')


def cart_view(request):
    cart = _get_cart(request)
    cart_items = []
    cart_total = 0
    max_quantity = 4

    for item in cart.values():
        item_total = item['unit_price'] * item['quantity']
        cart_total += item_total
        max_quantity = max(max_quantity, item['quantity'])
        cart_items.append({
            **item,
            'item_total': item_total,
        })

    coupon = _get_coupon(request)
    coupon_error, coupon_code_input = _pop_coupon_feedback(request)
    discount_amount = _get_discount_amount(cart_total, coupon)
    grand_total = max(cart_total - discount_amount, 0)
    available_coupons = _get_available_coupons(cart_total)
    razorpay_order_id = ''
    razorpay_amount = 0

    if grand_total > 0:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment = client.order.create(
            {
                'amount': int(grand_total * 100),
                'currency': 'INR',
                'payment_capture': '1',
            }
        )
        razorpay_order_id = payment.get('id', '')
        razorpay_amount = payment.get('amount', 0)
        request.session['pending_razorpay_order'] = {
            'order_id': razorpay_order_id,
            'amount': razorpay_amount,
        }
        request.session.modified = True

    return render(
        request,
        'cart/cart.html',
        {
            'cart_items': cart_items,
            'cart_total': cart_total,
            'discount_amount': discount_amount,
            'grand_total': grand_total,
            'applied_coupon': coupon,
            'coupon_error': coupon_error,
            'coupon_code_input': coupon_code_input,
            'available_coupons': available_coupons,
            'quantity_options': range(1, max_quantity + 5),
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_amount': razorpay_amount,
        },
    )


def update_cart_item(request, item_key):
    cart = _get_cart(request)
    item = cart.get(item_key)
    if not item:
        return redirect('cart')

    try:
        quantity = max(1, int(request.POST.get('quantity', '1')))
    except ValueError:
        quantity = 1

    item['quantity'] = quantity
    cart[item_key] = item
    _save_cart(request, cart)
    return redirect('cart')


def remove_cart_item(request, item_key):
    cart = _get_cart(request)
    if item_key in cart:
        cart.pop(item_key)
        _save_cart(request, cart)
        messages.success(request, 'Item removed from cart.')
    return redirect('cart')


def apply_coupon(request):
    if request.method != 'POST':
        return redirect('cart')

    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    coupon = Coupon.objects.filter(Coupon_code__iexact=coupon_code).first()
    cart_total = sum(item['unit_price'] * item['quantity'] for item in _get_cart(request).values())

    if not coupon:
        _clear_coupon(request)
        _set_coupon_error(request, 'Invalid Coupon.', coupon_code)
        return redirect('cart')

    if not coupon.is_valid():
        _clear_coupon(request)
        _set_coupon_error(request, 'This coupon has expired.', coupon_code)
        return redirect('cart')

    if cart_total < coupon.minimum_amount:
        _clear_coupon(request)
        _set_coupon_error(
            request,
            f'Coupon is valid for orders above {coupon.minimum_amount}.',
            coupon_code,
        )
        return redirect('cart')

    _save_coupon(
        request,
        {
            'code': coupon.Coupon_code,
            'discount_price': coupon.discount_price,
            'minimum_amount': coupon.minimum_amount,
            'expires_at': coupon.expires_at.isoformat() if coupon.expires_at else '',
        },
    )
    messages.success(request, f'Coupon {coupon.Coupon_code} applied successfully.')
    return redirect('cart')


def remove_coupon(request):
    _clear_coupon(request)
    messages.success(request, 'Coupon removed.')
    return redirect('cart')


@login_required
@require_POST
def verify_payment(request):
    Cart = apps.get_model('accounts', 'Cart')
    CartItems = apps.get_model('accounts', 'CartItems')
    razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
    razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
    razorpay_signature = request.POST.get('razorpay_signature', '').strip()

    pending_order = request.session.get('pending_razorpay_order', {})
    if not razorpay_order_id or pending_order.get('order_id') != razorpay_order_id:
        return JsonResponse({'success': False, 'message': 'Invalid payment order.'}, status=400)

    cart = _get_cart(request)
    if not cart:
        return JsonResponse({'success': False, 'message': 'Your cart is empty.'}, status=400)

    cart_total = _get_cart_total(cart)
    coupon_data = _get_coupon(request)
    discount_amount = _get_discount_amount(cart_total, coupon_data)
    grand_total = max(cart_total - discount_amount, 0)
    expected_amount = int(grand_total * 100)

    if pending_order.get('amount') != expected_amount:
        return JsonResponse({'success': False, 'message': 'Payment amount mismatch.'}, status=400)

    existing_cart = Cart.objects.filter(
        razor_pay_order_id=razorpay_order_id,
        razor_pay_payment_id=razorpay_payment_id,
        is_paid=True,
    ).first()
    if existing_cart:
        return JsonResponse({'success': True, 'redirect_url': '/product/cart/'})

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature(
            {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            }
        )
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({'success': False, 'message': 'Payment verification failed.'}, status=400)

    coupon_obj = None
    if coupon_data:
        coupon_obj = Coupon.objects.filter(Coupon_code__iexact=coupon_data.get('code', '')).first()

    purchased_cart = Cart.objects.create(
        user=request.user,
        coupon=coupon_obj,
        is_paid=True,
        razor_pay_order_id=razorpay_order_id,
        razor_pay_payment_id=razorpay_payment_id,
        razor_pay_payment_signature=razorpay_signature,
    )

    for item in cart.values():
        product = Product.objects.filter(slug=item['slug']).first()
        if not product:
            continue

        CartItems.objects.create(
            cart=purchased_cart,
            product=product,
            quantity=item['quantity'],
            size=item.get('size', ''),
            unit_price=item['unit_price'],
        )

    request.session['cart'] = {}
    request.session.pop('coupon', None)
    request.session.pop('coupon_error', None)
    request.session.pop('coupon_code_input', None)
    request.session.pop('pending_razorpay_order', None)
    request.session.modified = True
    messages.success(request, 'Payment successful. Your purchase has been saved.')

    return JsonResponse({'success': True, 'redirect_url': '/product/cart/'})
