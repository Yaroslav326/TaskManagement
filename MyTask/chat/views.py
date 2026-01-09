from django.shortcuts import render
from django.http import JsonResponse
from company.models import Department
from authentication.models import User
from rest_framework import authentication
from django.conf import settings
import jwt


def get_user_payload(request):
    auth_header = authentication.get_authorization_header(request).split()
    if len(auth_header) == 2:
        token = auth_header[1].decode('utf-8')
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return None, JsonResponse({'error': 'Invalid token'}, status=401)

    token = request.COOKIES.get('jwt')
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return None, JsonResponse({'error': 'Invalid token'}, status=401)

    return None, JsonResponse({'error': 'Authorization required'}, status=401)


def chat_view(request, room_name=None):
    payload, error = get_user_payload(request)

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    chats = [
        {'room_name': 'company', 'display_name': 'Общий чат'}
    ]

    user_departments = Department.objects.filter(personnel=user)
    for dept in user_departments:
        chats.append({
            'room_name': f'department_{dept.id}',
            'display_name': f' {dept.name}'
        })

    return render(request, 'chat.html', {
        'chats_json': chats,
        'user': user
    })
