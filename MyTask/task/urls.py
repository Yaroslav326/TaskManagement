from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.task_kanban, name='kanban_board'),
    path('add-task/', views.add_task, name='add_task'),
    path('add-subtask/', views.add_subtask, name='add_subtask'),
    path('update-task-status/', views.update_task_status, name='update_task_status'),
    path('delete-task-ajax/', views.delete_task_ajax, name='delete_task_ajax'),
    path('delete-subtask-ajax/', views.delete_subtask_ajax, name='delete_subtask_ajax'),
    path('toggle-subtask-ajax/', views.toggle_subtask_ajax, name='toggle_subtask_ajax'),
    path('edit-task-ajax/', views.edit_task_ajax, name='edit_task_ajax'),
    path ('update-task_status/', views.update_task_status, name='update_task_status'),
    path('edit-task-ajax/', views.edit_task_ajax, name='edit_task_ajax'),
    path('update-subtask-status/', views.update_subtask_status, name='update_subtask_status'),
    path('edit-subtask-ajax/', views.edit_subtask_ajax, name='edit_subtask_ajax'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('take-task-ajax/', views.take_task_ajax, name='take_task_ajax'),
]
