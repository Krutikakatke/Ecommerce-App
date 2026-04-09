from django.contrib import messages
from django.shortcuts import redirect, render

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
