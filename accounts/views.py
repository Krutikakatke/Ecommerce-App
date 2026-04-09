from django.shortcuts import redirect, render
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from smtplib import SMTPAuthenticationError
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from base.emails import send_account_activation_email
from accounts.models import Profile


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

