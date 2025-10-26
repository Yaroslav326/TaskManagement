from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views import (RegisterAPIView, LoginAPIView, UserRetrieveUpdateAPIView,
                    RegisterView, LoginView)

app_name = 'authentication'
urlpatterns = [
    path('users/', RegisterAPIView.as_view()),
    path('users/login/', LoginAPIView.as_view()),
    path('users/update/', csrf_exempt(UserRetrieveUpdateAPIView.as_view())),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
]
