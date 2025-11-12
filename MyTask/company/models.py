from django.db import models
from authentication.models import User


class Company(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=50)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    personnel = models.ManyToManyField(User, related_name='assigned_departments')

    def __str__(self):
        return self.name
