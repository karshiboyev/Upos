from django.db import models
from django.db.models import Model


class User(Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    password = models.CharField(max_length=100)
