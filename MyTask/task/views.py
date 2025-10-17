from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, Value, IntegerField, When
from .models import Task, Subtask
from .forms import TaskForm, SubtaskForm
import json


def task_kanban(request):
    tasks = Task.objects.annotate(
        sort_order=Case(
            When(status='todo', then=Value(0)),
            When(status='in_progress', then=Value(1)),
            When(status='done', then=Value(2)),
            default=Value(3),
            output_field=IntegerField()
        )
    ).order_by('sort_order')

    if request.method == 'POST':
        if 'add_task' in request.POST:
            form = TaskForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('kanban_board')

        elif 'add_subtask' in request.POST:
            task_id = request.POST.get('task_id')
            subtask_title = request.POST.get('subtask_title')
            try:
                task = Task.objects.get(id=task_id)
                Subtask.objects.create(task=task, title=subtask_title)
                return redirect('kanban_board')
            except Task.DoesNotExist:
                return redirect('kanban_board')

        elif 'update_status' in request.POST:
            task_id = request.POST.get('task_id')
            new_status = request.POST.get('new_status')
            try:
                task = Task.objects.get(id=task_id)
                task.status = new_status
                task.save()
                return redirect('kanban_board')
            except Task.DoesNotExist:
                return redirect('kanban_board')

        elif 'delete_task' in request.POST:
            task_id = request.POST.get('task_id')
            try:
                task = Task.objects.get(id=task_id)
                task.delete()
                return redirect('kanban_board')
            except Task.DoesNotExist:
                return redirect('kanban_board')

        elif 'delete_subtask' in request.POST:
            subtask_id = request.POST.get('subtask_id')
            try:
                subtask = Subtask.objects.get(id=subtask_id)
                subtask.delete()
                return redirect('kanban_board')
            except Subtask.DoesNotExist:
                return redirect('kanban_board')

    else:
        task_form = TaskForm()
        subtask_form = SubtaskForm()

    return render(request, 'task_kanban.html', {
        'tasks': tasks,
        'task_form': task_form,
        'subtask_form': subtask_form
    })


@csrf_exempt
@require_http_methods(["POST"])
def add_task(request):
    data = json.loads(request.body)
    title = data.get('title', '').strip()
    if not title:
        return JsonResponse({'error': 'Title is required'}, status=400)

    try:
        task = Task.objects.create(
            title=title,
            status='todo',
            employee=request.user
        )
        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'html': f"""
            <div class="card" id="card-{task.id}">
                <strong>{task.title}</strong>
                <p>{task.remark or ''}</p>
                <button onclick="deleteTask({task.id})">Delete</button>
                <select onchange="updateTaskStatus({task.id}, this.value)">
                    <option value="todo" selected>Todo</option>
                    <option value="in_progress">In Progress</option>
                    <option value="done">Done</option>
                </select>
            </div>
            """
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def add_subtask(request):
    try:
        data = json.loads(request.body)  # Получаем данные из тела запроса
        task_id = int(data.get('task_id'))
        subtask_title = data.get('subtask_title')
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing task ID'},
                            status=400)

    if not task_id or not subtask_title:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        task_id = int(task_id)  # Попробуйте преобразовать в число
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
def update_task_status(request):
    task_id = request.POST.get('task_id')
    new_status = request.POST.get('new_status')

    if not task_id or not new_status:
        return JsonResponse({'error': 'Missing required data'},
                            status=400)

    try:
        task = Task.objects.get(id=task_id)
        task.status = new_status
        task.save()
        return JsonResponse({'status': task.status})
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_task_ajax(request):
    try:
        data = json.loads(request.body)  # Получаем данные из тела запроса
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
def delete_subtask_ajax(request):
    try:
        data = json.loads(request.body)
        subtask_id = int(data.get('subtask_id'))
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid or missing data'}, status=400)

    if not subtask_id:
        if not subtask_id:
            return JsonResponse({'error': 'Missing subtask ID'}, status=400)
        else:
            try:
                subtask = Subtask.objects.get(id=subtask_id)
                subtask.delete()
                return JsonResponse({'success': True})
            except Subtask.DoesNotExist:
                if not subtask_id:
                    return JsonResponse({'error': 'Subtask not found'}, status=404)
                else:
                    return JsonResponse({'error': 'Subtask not found'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def edit_subtask_ajax(request):
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
def toggle_subtask_ajax(request):
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
def edit_task_ajax(request):
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
def update_task_status(request):
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
def update_subtask_status(request):
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
