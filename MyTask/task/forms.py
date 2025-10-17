from django import forms
from .models import Task, Subtask


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'status']


class SubtaskForm(forms.ModelForm):
    class Meta:
        model = Subtask
        fields = ['title']
