from django.db import models
from model_utils.models import TimeStampedModel
from exchange_core.models import BaseModel


class Card(TimeStampedModel, BaseModel, models.Model):
    account = models.ForeignKey('exchange_core.Accounts', related_name='cards', on_delete=models.CASCADE)
    number = models.CharField(max_length=16)
    