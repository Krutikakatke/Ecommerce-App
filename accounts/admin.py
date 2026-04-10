from django.contrib import admin
from .models import Cart, CartItems, Profile
# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_email_verified']
    search_fields = ['user__username', 'user__email']


class CartItemsInline(admin.TabularInline):
    model = CartItems
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'coupon', 'is_paid']
    list_filter = ['is_paid']
    search_fields = ['user__username', 'razor_pay_order_id', 'razor_pay_payment_id']
    inlines = [CartItemsInline]


@admin.register(CartItems)
class CartItemsAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'unit_price']
    search_fields = ['product__product_name', 'cart__user__username']
