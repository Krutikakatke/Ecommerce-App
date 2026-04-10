from django.urls import path
from products.views import (
    add_to_cart,
    apply_coupon,
    cart_view,
    get_product,
    remove_cart_item,
    remove_coupon,
    update_cart_item,
    verify_payment,
    
)

urlpatterns = [
    path('cart/', cart_view, name="cart"),
    path('cart/coupon/apply/', apply_coupon, name="apply_coupon"),
    path('cart/coupon/remove/', remove_coupon, name="remove_coupon"),
    path('cart/verify-payment/', verify_payment, name="verify_payment"),
    path('cart/remove/<str:item_key>/', remove_cart_item, name="remove_cart_item"),
    path('cart/update/<str:item_key>/', update_cart_item, name="update_cart_item"),
    path('add-to-cart/<slug:slug>/', add_to_cart, name="add_to_cart"),
    path('<slug>/' , get_product , name="get_product"),
    
]

 
