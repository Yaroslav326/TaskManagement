from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def chat_page(request):
    return render(request, 'chat.html', {
        'chatroom_name': 'general'
    })
