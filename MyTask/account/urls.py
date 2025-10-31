from django.urls import path
from . import views

app_name = 'account'
urlpatterns = [
    path('my-tasks/', views.get_user_task, name='get_user_task'),
    path('', views.user_task, name='user_task'),
    path('update-account/', views.update_account, name='update_account'),
]
