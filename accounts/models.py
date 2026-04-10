from django.db import models
from django.contrib.auth.models import User
from base.models import BaseModel
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from products.models import Coupon, Product

class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    is_email_verified = models.BooleanField(default=False)
    email_token = models.CharField(max_length=100, null=True, blank=True)
    Profile_image = models.ImageField(upload_to="profile")

    def __str__(self):
        return self.user.username


class Cart(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carts")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="carts")
    is_paid = models.BooleanField(default=False)
    razor_pay_order_id = models.CharField(max_length=255, null=True, blank=True)
    razor_pay_payment_id = models.CharField(max_length=255, null=True, blank=True)
    razor_pay_payment_signature = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Cart object ({self.uid})"


class CartItems(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=100, null=True, blank=True)
    unit_price = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.product_name} x {self.quantity}"

@receiver(post_save , sender = User)
def send_email_token(sender , instance , created , **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            email_token=str(uuid.uuid4()),
        )
