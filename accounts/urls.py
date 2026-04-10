from accounts.views import account_section, activate_email, invoice_view, login_page, logout_page, register_pages
from django.urls import path

urlpatterns = [
    path('login/' ,login_page , name='login'),
    path('register/' ,register_pages , name='register'),
    path('logout/' ,logout_page , name='logout'),
    path('activate/<str:email_token>/' ,activate_email , name='activate_email'),
    path('profile/' ,account_section , name='account_profile'),
    path('profile/<str:section>/' ,account_section , name='account_section'),
    path('invoice/<uuid:order_id>/' ,invoice_view , name='invoice'),
]
