from django.db import models


class Session_counter(models.Model):
    address_url = models.CharField(max_length=500, null=True)
    count = models.IntegerField(default=0)
