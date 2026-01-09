import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from authentication.models import User
from channels.auth import AuthMiddlewareStack
import logging

logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user_from_payload(payload):
    """Асинхронно получает пользователя по payload['user_id']"""
    try:
        user_id = payload.get('user_id')
        if user_id is None:
            return AnonymousUser()
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Мидлвар для аутентификации WebSocket-соединений через JWT.
    Поддерживает:
      - Заголовок Authorization: Token <token>
      - Куку jwt=...
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])

        token = None

        if b'authorization' in headers:
            auth_header = headers[b'authorization'].decode('utf-8')
            parts = auth_header.split()
            if len(parts) == 2:
                token = parts[1]

        if token is None and b'cookie' in headers:
            cookie_header = headers[b'cookie'].decode('utf-8')
            cookie_parts = cookie_header.split('; ')
            for part in cookie_parts:
                if part.startswith('jwt='):
                    token = part.split('=', 1)[1]
                    break

        if token is None:
            scope['user'] = AnonymousUser()
            return await self.app(scope, receive, send)

        try:
            payload = jwt.decode(token, settings.SECRET_KEY,
                                 algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            scope['user'] = AnonymousUser()
            return await self.app(scope, receive, send)
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            scope['user'] = AnonymousUser()
            return await self.app(scope, receive, send)

        user = await get_user_from_payload(payload)
        scope['user'] = user

        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(app):
    return JWTAuthMiddleware(AuthMiddlewareStack(app))
