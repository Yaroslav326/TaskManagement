from django.urls import path
from .views import RegisterAPIView

app_name = 'authentication'
urlpatterns = [
    path('users/', RegisterAPIView.as_view()),
]
