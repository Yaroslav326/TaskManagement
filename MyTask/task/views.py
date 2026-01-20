from typing import Dict, Any, Optional, Tuple, List
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, Value, IntegerField, When, Q
from django.template.loader import render_to_string
from .models import Task, Subtask
from .forms import TaskForm, SubtaskForm
from rest_framework import authentication
from django.conf import settings
from send_mail.tasks import send_email_task
from datetime import date
from authentication.models import User
from company.models import Department
from loguru import logger
import jwt
import json

logger.add("logs_task.log", rotation="500 MB")


def get_user_payload(request: HttpRequest) -> (
        Tuple)[Optional[Dict[str, Any]], Optional[JsonResponse]]:
    """
    Извлекает и декодирует JWT-токен из заголовка Authorization или
    куки запроса.

    Args:
        request (HttpRequest): Объект HTTP-запроса, содержащий
        заголовки и куки.

    Returns:
        tuple: (payload: dict or None, error: JsonResponse or None)
    """
    auth_header = authentication.get_authorization_header(request).split()
    if len(auth_header) == 2:
        token = auth_header[1].decode('utf-8')
    else:
        token = request.COOKIES.get('jwt')
        if not token:
            return None, JsonResponse(
                {'error': 'Authorization header or cookie missing'}, status=401
            )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        logger.info(f"Payload: {payload}")
        return payload, None
    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        return None, JsonResponse({'error': 'Token expired'}, status=401)
    except jwt.InvalidTokenError:
        logger.error("Invalid token")
        return None, JsonResponse({'error': 'Invalid token'}, status=401)


def parse_json_body(request: HttpRequest) -> (
        Tuple)[Dict[str, Any] | List[Any] | None, Optional[JsonResponse]]:
    """
    Парсит тело HTTP-запроса как JSON.

    Args:
        request (HttpRequest): Объект HTTP-запроса с телом в формате JSON.

    Returns:
        tuple: (data: dict/list or None, error: JsonResponse or None)
    """
    try:
        logger.info(f"Request body: {request.body}")
        data = json.loads(request.body)
        return data, None
    except json.JSONDecodeError:
        logger.error("Invalid JSON")
        return {}, JsonResponse({'error': 'Invalid JSON'}, status=400)


def company_tasks(request: HttpRequest) -> Tuple[Any, Optional[JsonResponse]]:
    """
    Возвращает QuerySet задач, связанных с пользователями из компании текущего
    пользователя.

    Returns:
        tuple: (tasks: QuerySet or empty, error: JsonResponse or None)
    """
    payload, error = get_user_payload(request)
    if error:
        return Task.objects.none(), error

    try:
        user = User.objects.get(id=payload['user_id'])
        logger.info(f"User: {user}")
    except User.DoesNotExist:
        logger.error(f"User not found, id: {payload['user_id']}")
        return JsonResponse({'error': 'User not found'}, status=404), None

    company_id = (Department.objects.filter(personnel=user).values_list
                  ('company_id', flat=True).first())
    if not company_id:
        return Task.objects.none(), None

    users_in_company = (User.objects.filter
                        (assigned_departments__company_id=company_id).distinct())

    tasks = Task.objects.filter(
        Q(customer__in=users_in_company) | Q(employee__in=users_in_company)
    ).distinct()

    return tasks, None


def task_kanban(request: HttpRequest) -> HttpResponse:
    """
    Отображение доски Kanban с задачами.

    Returns:
        HttpResponse: HTML-страница с задачами.
    """
    tasks, error = company_tasks(request)
    if error:
        return error

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
        'status_choices': Task.STATUS_CHOICES,
        'today': date.today()
    })


def render_task_card(request: HttpRequest, task: Task) -> str:
    """
    Рендерит HTML карточки задачи.

    Returns:
        str: HTML-строка карточки задачи.
    """
    html = render_to_string('task_card.html',
                            {'task': task}, request=request)
    return html.strip()


def render_subtask_card(request: HttpRequest, subtask: Subtask) -> str:
    """
    Рендерит HTML карточки подзадачи.

    Returns:
        str: HTML-строка карточки подзадачи.
    """
    html = render_to_string('subtask_card.html',
                            {'subtask': subtask}, request=request)
    return html.strip()


@csrf_exempt
@require_http_methods(["POST"])
def add_task(request: HttpRequest) -> JsonResponse:
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)
    if error:
        return error

    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title is required'}, status=400)

    try:
        task = Task.objects.create(customer=user, title=title, status='todo')
        logger.info(f"Task created: {task}")
        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'html': render_task_card(request, task)
        })
    except Exception as e:
        logger.error(f"Error creating task: {e}, data: {data}, "
                     f"payload: {payload}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_subtask(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        task_id = int(data.get('task_id'))
        subtask_title = data.get('subtask_title', '').strip()
        logger.info(f"Subtask data: {data}")
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing task ID")
        return JsonResponse({'error': 'Invalid or missing task ID'},
                            status=400)

    if not task_id or not subtask_title:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
        logger.info(f"Task found: {task}")
    except Task.DoesNotExist:
        logger.error(f"Task not found, id: {task_id}")
        return JsonResponse({'error': 'Task not found'}, status=404)

    subtask = Subtask.objects.create(task=task, title=subtask_title)
    return JsonResponse({
        'id': subtask.id,
        'title': subtask.title,
        'is_accomplished': subtask.is_accomplished,
        'html': render_subtask_card(request, subtask)
    })


@csrf_exempt
@require_http_methods(["POST"])
def delete_task_ajax(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        task_id = int(data.get('task_id'))
        logger.info(f"Task ID: {task_id}")
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing task ID")
        return JsonResponse({'error': 'Invalid or missing task ID'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.delete()
        logger.info(f"Task deleted: {task}")
        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        logger.error(f"Task not found, id: {task_id}")
        return JsonResponse({'error': 'Task not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_subtask_ajax(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        subtask_id = int(data.get('subtask_id'))
        logger.info(f"Subtask ID: {subtask_id}")
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing subtask ID")
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    if not subtask_id:
        return JsonResponse({'error': 'Missing subtask ID'}, status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.delete()
        logger.info(f"Subtask deleted: {subtask}")
        return JsonResponse({'success': True})
    except Subtask.DoesNotExist:
        logger.error(f"Subtask not found, id: {subtask_id}")
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting subtask: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def edit_subtask_ajax(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        subtask_id = int(data.get('subtask_id'))
        title = data.get('title', '').strip()
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing data")
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    if not subtask_id or not title:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.title = title
        subtask.save()
        logger.info(f"Subtask updated: {subtask}")
        return JsonResponse({
            'id': subtask.id,
            'title': subtask.title,
            'is_accomplished': subtask.is_accomplished
        })
    except Subtask.DoesNotExist:
        logger.error(f"Subtask not found, id: {subtask_id}")
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating subtask: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_subtask_ajax(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        subtask_id = int(data.get('subtask_id'))
        is_completed = data.get('is_completed') == 'true'
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing data")
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    if not subtask_id:
        return JsonResponse({'error': 'Missing subtask ID'}, status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.is_accomplished = is_completed
        subtask.save()
        logger.info(f"Subtask updated: {subtask}")
        return JsonResponse({'is_accomplished': subtask.is_accomplished})
    except Subtask.DoesNotExist:
        logger.error(f"Subtask not found, id: {subtask_id}")
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating subtask: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def edit_task_ajax(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        task_id = int(data.get('task_id'))
        title = data.get('title', '').strip()
        remark = data.get('remark', '').strip()
        end_date_str = data.get('end_date')
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing data")
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    if not task_id or not title:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        logger.error(f"Task not found, id: {task_id}")
        return JsonResponse({'error': 'Task not found'}, status=404)

    end_date = None
    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            logger.error(f"Invalid date format: {end_date_str}")
            return JsonResponse(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=400)

    task.title = title
    task.remark = remark
    task.date_end = end_date
    task.save()

    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'remark': task.remark,
        'status': task.status,
        'date_start': task.date_start.strftime('%Y-%m-%d'),
        'date_end': task.date_end.strftime('%Y-%m-%d')
        if task.date_end else None,
    })


@csrf_exempt
@require_http_methods(["POST"])
def update_task_status(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        task_id = int(data.get('task_id'))
        new_status = data.get('new_status')
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing data")
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    if not task_id or not new_status:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.status = new_status
        task.save()
        send_email_task.delay(
            subject="Изменение статуса задачи",
            message=f"Задача '{task.title}' стала в статус '{new_status}'.",
            recipient_list=[task.customer.email]
        )
        logger.info(f"Task updated: {task}")
        return JsonResponse({'status': task.status})
    except Task.DoesNotExist:
        logger.error(f"Task not found, id: {task_id}")
        return JsonResponse({'error': 'Task not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_subtask_status(request: HttpRequest) -> JsonResponse:
    data, error = parse_json_body(request)
    if error:
        return error

    try:
        subtask_id = int(data.get('subtask_id'))
        new_status = data.get('new_status')
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing data")
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    if not subtask_id or not new_status:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        subtask = Subtask.objects.get(id=subtask_id)
        subtask.status = new_status
        subtask.save()
        logger.info(f"Subtask updated: {subtask}")
        return JsonResponse({'status': subtask.status})
    except Subtask.DoesNotExist:
        logger.error(f"Subtask not found, id: {subtask_id}")
        return JsonResponse({'error': 'Subtask not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating subtask: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def take_task_ajax(request: HttpRequest) -> JsonResponse:
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)
    if error:
        return error

    try:
        task_id = int(data.get('task_id'))
    except (ValueError, TypeError, KeyError):
        logger.error("Invalid or missing data")
        return JsonResponse({'error': 'Invalid or missing data'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.take_task(user)
        send_email_task.delay(
            subject="Назначение задачи",
            message=f"Задача '{task.title}' была назначена {user.username}.",
            recipient_list=[task.customer.email]
        )
        logger.info(f"Task taken by {user.username}")
        return JsonResponse({'success': True, 'username': user.username})
    except Task.DoesNotExist:
        logger.error(f"Task not found, id: {task_id}")
        return JsonResponse({'error': 'Task not found'}, status=404)
