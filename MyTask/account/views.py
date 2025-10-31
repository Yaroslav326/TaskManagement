from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, Value, IntegerField, When
from task.models import Task, Subtask
from task.forms import TaskForm, SubtaskForm
from rest_framework import authentication
from django.conf import settings
from authentication.models import User
import jwt
import json


def user_task(request):
    return render(request, 'user_task.html', {
        'status_choices': Task.STATUS_CHOICES
    })


@csrf_exempt
@require_http_methods(["POST"])
def get_user_task(request):
    try:
        request.user = None
        auth_header = authentication.get_authorization_header(request).split()
        if len(auth_header) != 2:
            return JsonResponse(
                {'error': 'Authorization header missing or malformed'},
                status=401)

        token = auth_header[1].decode('utf-8')
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user = User.objects.get(id=payload['user_id'])

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}

        status_filter = data.get('status', '')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')

        tasks = Task.objects.filter(employee=user)

        if status_filter:
            tasks = tasks.filter(status=status_filter)

        if start_date:
            tasks = tasks.filter(date_start__gte=start_date)
        if end_date:
            tasks = tasks.filter(date_start__lte=end_date)

        tasks = tasks.annotate(
            sort_order=Case(
                When(status='todo', then=Value(0)),
                When(status='in_progress', then=Value(1)),
                When(status='done', then=Value(2)),
                default=Value(3),
                output_field=IntegerField()
            )
        ).order_by('sort_order')

        html = render(request, 'task_list.html', {
            'tasks': tasks,
            'task_form': TaskForm(),
            'subtask_form': SubtaskForm(),
        }).content.decode('utf-8')

        return JsonResponse({'html': html})

    except jwt.ExpiredSignatureError:
        return JsonResponse({'error': 'Token expired'}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({'error': 'Invalid token'}, status=401)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
