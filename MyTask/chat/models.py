from django.db import models
from authentication.models import User
from company.models import Company, Department


class Message(models.Model):
    message = models.TextField(max_length=1000)
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='messages')
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE,
                                   null=True)
