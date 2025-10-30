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
    print(request.headers)
    request.user = None
    auth_header = authentication.get_authorization_header(request).split()
    print(auth_header)

    token = auth_header[1].decode('utf-8')
    pyload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

    user = User.objects.get(id=pyload['user_id'])

    tasks = Task.objects.filter(user=user).annotate(
        sort_order=Case(
            When(status='todo', then=Value(0)),
            When(status='in_progress', then=Value(1)),
            When(status='done', then=Value(2)),
            default=Value(3),
            output_field=IntegerField()
        )
    ).order_by('sort_order')

    task_form = TaskForm()
    subtask_form = SubtaskForm()

    return render(request, 'user_task.html', {
        'tasks': tasks,
        'task_form': task_form,
        'subtask_form': subtask_form
    })
