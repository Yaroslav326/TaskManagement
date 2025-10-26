from django import forms
from .models import Task, Subtask


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'status', 'date_end', 'remark']
        widgets = {
            'date_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class SubtaskForm(forms.ModelForm):
    class Meta:
        model = Subtask
        fields = ['title']