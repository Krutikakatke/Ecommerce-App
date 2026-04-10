from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from smtplib import SMTPAuthenticationError
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from base.emails import send_account_activation_email
from accounts.models import Cart, Profile
from products.models import Coupon


# Create your views here.
def login_page(request):
        if request.method == 'POST':
            email = request.POST.get('email')
            password = request.POST.get('password')
            user_obj = User.objects.filter(username = email)

            if not user_obj.exists():
                messages.warning(request, "Account not found.")
                return HttpResponseRedirect(request.path_info)
            
            if not user_obj[0].profile.is_email_verified:
                 messages.warning(request, 'Your account is not verified.')
                 return HttpResponseRedirect(request.path_info)
        
            user_obj = authenticate(username=email, password=password)
            if user_obj:
                login(request, user_obj)
                return redirect('/')

            messages.warning(request, "Invalid email or password.")
            return HttpResponseRedirect(request.path_info)
    
        return render(request ,'accounts/login.html')


def register_pages(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')

        try:
            validate_email(email)
        except ValidationError:
            messages.warning(request, "Please enter a valid email address.")
            return HttpResponseRedirect(request.path_info)

        user_obj = User.objects.filter(username = email)

        if user_obj.exists():
            messages.warning(request, "Email is already taken.")
            return HttpResponseRedirect(request.path_info)
        
        user_obj = User.objects.create(first_name=first_name, last_name=last_name, email=email, username=email)
        user_obj.set_password(password)
        user_obj.save()

        profile = Profile.objects.get(user=user_obj)
        try:
            send_account_activation_email(
                user_obj.email,
                profile.email_token,
                request.get_host(),
            )
            messages.success(request, "A verification email has been sent to your inbox.")
        except SMTPAuthenticationError:
            messages.warning(
                request,
                "Account created, but Gmail rejected the sender login. "
                "Check EMAIL_HOST_USER and use a Google App Password for EMAIL_HOST_PASSWORD.",
            )
        except Exception as exc:
            messages.warning(request, f"Account created, but email could not be sent: {exc}")

        return HttpResponseRedirect(request.path_info)
    
    return render(request ,'accounts/register.html')


def activate_email(request, email_token):
    profile = Profile.objects.filter(email_token=email_token).select_related('user').first()

    if not profile:
        messages.warning(request, "Invalid activation link.")
        return redirect('login')

    profile.is_email_verified = True
    profile.email_token = None
    profile.save(update_fields=['is_email_verified', 'email_token'])

    messages.success(request, "Your email has been verified. You can sign in now.")
    return redirect('login')


def logout_page(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect('login')


def _get_delivery_status(order):
    days_since_order = (timezone.now() - order.updated_at).days
    if days_since_order <= 0:
        return "Order confirmed", "Your order has been placed and is waiting for packaging."
    if days_since_order <= 2:
        return "Packed", "Your shipment is packed and ready to leave the warehouse."
    if days_since_order <= 4:
        return "Shipped", "Your package is on the way to the delivery hub."
    if days_since_order <= 6:
        return "Out for delivery", "Your shipment is with the delivery partner and should arrive soon."
    return "Delivered", "Your order has been delivered successfully."


def _build_order_summary(order):
    items = list(order.cart_items.all())
    item_count = sum(item.quantity for item in items)
    subtotal = sum(item.quantity * item.unit_price for item in items)
    discount_amount = order.coupon.discount_price if order.coupon else 0
    total_amount = max(subtotal - discount_amount, 0)
    status_label, status_description = _get_delivery_status(order)
    return {
        'order': order,
        'items': items,
        'item_count': item_count,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'total_amount': total_amount,
        'status_label': status_label,
        'status_description': status_description,
    }


def _get_user_orders(user):
    orders = (
        Cart.objects.filter(user=user, is_paid=True)
        .select_related('coupon')
        .prefetch_related('cart_items__product')
        .order_by('-updated_at')
    )
    order_cards = []

    for order in orders:
        order_cards.append(_build_order_summary(order))

    return order_cards


@login_required
def account_section(request, section='orders'):
    valid_sections = {'orders', 'wishlist', 'coupons', 'help-center', 'delivery', 'payment'}
    if section not in valid_sections:
        section = 'orders'

    order_cards = _get_user_orders(request.user)
    available_coupons = Coupon.objects.all().order_by('minimum_amount', 'Coupon_code')
    account_sections = {'orders', 'wishlist', 'coupons', 'help-center'}

    context = {
        'active_section': section,
        'order_cards': order_cards,
        'available_coupons': available_coupons,
        'show_account_menu': section in account_sections,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(
        Cart.objects.select_related('coupon', 'user').prefetch_related('cart_items__product'),
        uid=order_id,
        user=request.user,
        is_paid=True,
    )
    summary = _build_order_summary(order)
    context = {
        'invoice': summary,
        'customer_name': request.user.get_full_name() or request.user.username,
        'customer_address': request.user.email,
        'payment_method': 'Razorpay',
    }
    return render(request, 'accounts/invoice.html', context)
