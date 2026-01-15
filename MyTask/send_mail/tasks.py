from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_email_task(subject, message, recipient_list):
    return send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=recipient_list,
        fail_silently=False,
    )

