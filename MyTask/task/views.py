from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, Value, IntegerField, When
from .models import Task, Subtask
from .forms import TaskForm, SubtaskForm
from rest_framework import authentication
from django.conf import settings
from authentication.models import User
import jwt
import json


def task_kanban(request) -> HttpResponse:
    """
    Функция отображения и сортировки доски Kanban с задачами.

    Обрабатывает запросы GET и POST для управления задачами. При GET-запросе
    возвращает страницу с доской Kanban, сортируя задачи по статусам.
    При POST-запросе обрабатывает сортировку

    Args: request: HttpRequest - объект HTTP-запроса,
    содержащий информацию о методе запроса и данных формы

    Returns: HttpResponse - объект HTTP-ответа, содержащий HTML-страницу доски
    Kanban или редирект на неё
    """

    tasks = Task.objects.all()

    status_filter = request.GET.get('status')
    if status_filter and status_filter in dict(Task.STATUS_CHOICES):
        tasks = tasks.filter(status=status_filter)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
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

    task_form = TaskForm()
    subtask_form = SubtaskForm()

    return render(request, 'task_kanban.html', {
        'tasks': tasks,
        'task_form': task_form,
        'subtask_form': subtask_form,
        'status_choices': Task.STATUS_CHOICES
    })


@csrf_exempt
@require_http_methods(["POST"])
def add_task(request) -> JsonResponse:
    """
    Функция добавления новой задачи.

    Обрабатывает AJAX-запросы на создание новой задачи. Получает данные из
    JSON-тела запроса, создает новую задачу и возвращает её HTML-представление.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с данными новой задачи и её
    HTML-представлением
    """

    data = json.loads(request.body)
    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title is required'}, status=400)

    try:
        task = Task.objects.create(
            title=title,
            status='todo'
        )
        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'html': f"""
            <div class="card" id="card-{task.id}">
                <strong>{task.title}</strong>
                <p>{task.remark or ''}</p>
                <p><small>Создано: {task.date_start.strftime('%Y-%m-%d %H:%M')}</small></p>
                <p><small>Окончание: {task.date_end.strftime('%Y-%m-%d %H:%M') if task.date_end else '—'}</small></p>
                <p><small>Исполнитель: {'Нет'}</small></p>
                <button onclick="deleteTask({task.id})">Delete</button>
                <select onchange="updateTaskStatus({task.id}, this.value)">
                    <option value="todo" selected>Todo</option>
                    <option value="in_progress">In Progress</option>
                    <option value="done">Done</option>
                </select>
                <button onclick="takeTask({task.id})">Взять задачу</button>
            </div>
            """
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_subtask(request) -> JsonResponse:
    """
    Функция добавления подзадачи к существующей задаче.

    Обрабатывает AJAX-запросы на создание новой подзадачи.
    Получает ID задачи и заголовок подзадачи из JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с данными новой подзадачи и её
    HTML-представлением
    """

    try:
        data = json.loads(request.body)
        task_id = int(data.get('task_id'))
        subtask_title = data.get('subtask_title')
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing task ID'},
                            status=400)

    if not task_id or not subtask_title:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        task_id = int(task_id)
    except ValueError:
        return JsonResponse({'error': 'Invalid task ID format'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)

    subtask = Subtask.objects.create(task=task, title=subtask_title)
    return JsonResponse({
        'id': subtask.id,
        'title': subtask.title,
        'is_accomplished': subtask.is_accomplished,
        'html': f"""
        <div class="card" id="subtask-{subtask.id}">
            <p>{subtask.title}</p>
            <button onclick="deleteSubtask({subtask.id})">Delete</button>
            <label>
                <input type="checkbox" {'checked' if subtask.is_accomplished else ''} onchange="toggleSubtaskStatus({subtask.id}, this.checked)">
                Accomplished
            </label>
        </div>
        """
    })


@csrf_exempt
@require_http_methods(["POST"])
def delete_task_ajax(request) -> JsonResponse:
    """
    Функция удаления задачи.

    Обрабатывает AJAX-запросы на удаление задачи. Получает ID задачи из
    JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с флагом успеха операции
    """

    try:
        data = json.loads(request.body)
        task_id = int(data.get('task_id'))
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing task ID'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.delete()
        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_subtask_ajax(request) -> JsonResponse:
    """
    Функция удаления подзадачи.

    Обрабатывает AJAX-запросы на удаление подзадачи. Получает ID подзадачи из
    JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с флагом успеха операции
    """

    try:
        data = json.loads(request.body)
        subtask_id = int(data.get('subtask_id'))
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    if not subtask_id:
        return JsonResponse({'error': 'Missing subtask ID'}, status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.delete()
        return JsonResponse({'success': True})
    except Subtask.DoesNotExist:
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def edit_subtask_ajax(request) -> JsonResponse:
    """
    Функция редактирования подзадачи.

    Обрабатывает AJAX-запросы на изменение заголовка подзадачи. Получает ID
    подзадачи и новый заголовок из JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с обновленными данными подзадачи
    """

    try:
        data = json.loads(request.body)
        subtask_id = int(data.get('subtask_id'))
        title = data.get('title', '').strip()
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    if not subtask_id or not title:
        return JsonResponse({'error': 'Missing required data'}, status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.title = title
        subtask.save()

        return JsonResponse({
            'id': subtask.id,
            'title': subtask.title,
            'is_accomplished': subtask.is_accomplished
        })
    except Subtask.DoesNotExist:
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_subtask_ajax(request) -> JsonResponse:
    """
    Функция изменения статуса завершения подзадачи.

    Обрабатывает AJAX-запросы на установку/сброс флага завершения подзадачи.
    Получает ID подзадачи и текущий статус из JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с обновленным статусом подзадачи
    """
    try:
        data = json.loads(request.body)
        subtask_id = int(data.get('subtask_id'))
        is_completed = data.get('is_completed') == 'true'
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    if not subtask_id:
        return JsonResponse({'error': 'Missing subtask ID'}, status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.is_accomplished = is_completed
        subtask.save()
        return JsonResponse({'is_accomplished': subtask.is_accomplished})
    except Subtask.DoesNotExist:
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def edit_task_ajax(request) -> JsonResponse:
    """
    Функция редактирования задачи.

    Обрабатывает AJAX-запросы на изменение заголовка и примечания задачи.
    Получает ID задачи, новый заголовок и примечание из JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с обновленными данными задачи
    """
    try:
        data = json.loads(request.body)
        task_id = int(data.get('task_id'))
        title = data.get('title', '').strip()
        remark = data.get('remark', '').strip()
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    if not task_id or not title:
        return JsonResponse({'error': 'Missing required data'}, status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.title = title
        task.remark = remark
        task.save()

        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'remark': task.remark,
            'status': task.status
        })
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_task_status(request) -> JsonResponse:
    """
    Функция обновления статуса задачи.

    Обрабатывает AJAX-запросы на изменение статуса задачи.
    Получает ID задачи и новый статус из JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с новым статусом задачи
    """

    try:
        data = json.loads(request.body)
        task_id = int(data.get('task_id'))
        new_status = data.get('new_status')
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    if not task_id or not new_status:
        return JsonResponse({'error': 'Missing required data'}, status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.status = new_status
        task.save()
        return JsonResponse({
            'status': task.status
        })
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_subtask_status(request) -> JsonResponse:
    """
    Функция обновления статуса подзадачи.

    Обрабатывает AJAX-запросы на изменение статуса подзадачи. Получает
    ID подзадачи и новый статус из JSON-тела запроса.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с новым статусом подзадачи
    """
    try:
        data = json.loads(request.body)
        subtask_id = int(data.get('subtask_id'))
        new_status = data.get('new_status')
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    if not subtask_id or not new_status:
        return JsonResponse({'error': 'Missing required data'}, status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.status = new_status
        subtask.save()
        return JsonResponse({
            'status': subtask.status
        })
    except Subtask.DoesNotExist:
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def take_task_ajax(request) -> JsonResponse:
    """
    Функция назначения задачи пользователю.

    Обрабатывает AJAX-запросы на привязку задачи к пользователю.
    Извлекает токен аутентификации из заголовка запроса, декодирует его,
    получает пользователя и привязывает задачу к нему.

    Args: request: HttpRequest - объект HTTP-запроса, содержащий JSON-данные

    Returns: JsonResponse - JSON-объект с флагом успеха операции и именем пользователя
    """

    request.user = None
    auth_header = authentication.get_authorization_header(request).split()

    token = auth_header[1].decode('utf-8')
    payload = jwt.decode(token, key=settings.SECRET_KEY, algorithms=['HS256'])

    user = User.objects.get(id=payload['user_id'])

    try:
        data = json.loads(request.body)
        task_id = int(data.get('task_id'))
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.take_task(user)
        return JsonResponse({
            'success': True,
            'username': user.username
        })
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
