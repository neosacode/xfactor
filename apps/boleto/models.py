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
    card = models.ForeignKey('card.Cards', related_name='boletos', on_delete=models.CASCADE, null=True)
    payer_name = models.CharField(max_length=20)
    payer_document = models.CharField(max_length=20)
    receipt = models.ImageField(null=True, blank=True, verbose_name=_("Receipt"))
    status = models.CharField(max_length=15, choices=STATUS, default=STATUS.created)

    class Meta:
        verbose_name = _("Boleto")
        verbose_name_plural = _("Boletos")

    @property
    def final(self):
        return self.barcode[-5:]


@admin.register(Boletos)
class BoletosAdmin(admin.ModelAdmin):
    list_display = ['barcode', 'card', 'amount', 'created']
    ordering = ('-created',)
    actions = None
