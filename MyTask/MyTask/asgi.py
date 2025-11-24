"""
ASGI config for MyTask project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MyTask.settings')

django_asgi_app = get_asgi_application()

from django.conf import settings
print("CHANNEL_LAYERS:", settings.CHANNEL_LAYERS)

from channels.routing import ProtocolTypeRouter, URLRouter
from chat.middleware import JWTAuthMiddlewareStack
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from chat import routing

class StaticFilesASGIHandler(ASGIStaticFilesHandler):
    """Кастомный handler для статики в ASGI"""
    pass


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})

