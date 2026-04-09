from accounts.views import activate_email, login_page, register_pages
from django.urls import path

urlpatterns = [
    path('login/' ,login_page , name='login'),
    path('register/' ,register_pages , name='register'),
    path('activate/<str:email_token>/' ,activate_email , name='activate_email'),
]
