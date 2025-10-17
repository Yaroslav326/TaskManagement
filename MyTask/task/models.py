from django.conf import settings
from django.db import models


class Task(models.Model):
    STATUS_CHOICES = (
        ('todo', 'Todo'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    )
    title = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='todo')
    date_start = models.DateTimeField(auto_now_add=True)
    date_end = models.DateTimeField(null=True)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 on_delete=models.CASCADE)
    remark = models.TextField(null=True)

    def __str__(self):
        return self.title


class Subtask(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE,
                             related_name='subtasks')
    title = models.TextField()
    is_accomplished = models.BooleanField(default=False)
    remark = models.TextField(null=True)

    def __str__(self):
        return self.title
