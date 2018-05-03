import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from model_utils import Choices
from model_utils.models import TimeStampedModel


class Boletos(TimeStampedModel, models.Model):
	STATUS = Choices('created', 'paid')

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	barcode = models.CharField(max_length=60)
	bank_name = models.CharField(max_length=30)
	amount = models.DecimalField(max_digits=20, decimal_places=8)
	expiration_date = models.DateField()
	payment_date = models.DateField(null=True, blank=True)
	checksum = models.CharField(max_length=1)
	user = models.ForeignKey('exchange_core.Users', related_name='boletos', on_delete=models.CASCADE)
	payer_name = models.CharField(max_length=20)
	payer_document = models.CharField(max_length=20)
	receipt = models.ImageField(null=True, blank=True, verbose_name=_("Receipt"))
	status = models.CharField(max_length=15, choices=STATUS, default=STATUS.created)


@admin.register(Boletos)
class BoletosAdmin(admin.ModelAdmin):
    list_display = ['barcode', 'user', 'amount', 'created']
    ordering = ('-created',)
    actions = None