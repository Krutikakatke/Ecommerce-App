from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.core.mail import send_mail


def send_account_activation_email(email, email_token, domain):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise ImproperlyConfigured(
            "EMAIL_HOST_USER and EMAIL_HOST_PASSWORD must be set before sending mail."
        )

    subject = 'Your account needs to be verified'
    email_from = settings.EMAIL_HOST_USER
    message = (
        f'Hi, click on the link to activate your account: '
        f'http://{domain}/accounts/activate/{email_token}/'
    )
    send_mail(subject, message, email_from, [email], fail_silently=False)
