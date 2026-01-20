from celery import shared_task
from django.core.mail import send_mail
from typing import List


@shared_task
def send_email_task(subject: str, message: str,
                    recipient_list: List[str]) -> int:
    """
    Асинхронная задача для отправки email через Celery.

    Эта задача использует Django `send_mail` для отправки текстового письма
    указанному списку получателей. Отправка происходит асинхронно через
    очередь Celery.

    Args:
        subject (str): Тема письма.
        message (str): Текстовое содержимое письма (не HTML).
        recipient_list (List[str]): Список email-адресов получателей.

    Returns:
        int: Количество успешно доставленных писем (обычно 1 при успехе).

    Raises:
        smtplib.SMTPException: Если отправка письма
        не удалась и fail_silently=False.
    """
    return send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=recipient_list,
        fail_silently=False,
    )

