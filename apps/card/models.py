from decimal import Decimal
from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from exchange_core.models import BaseModel
from exchange_core.admin import BaseAdmin


class Cards(TimeStampedModel, BaseModel, models.Model):
    account = models.ForeignKey('exchange_core.Accounts', related_name='cards', on_delete=models.CASCADE)
    number = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    document_1 = models.CharField(max_length=30, null=True, blank=True)
    document_2 = models.CharField(max_length=30, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    mothers_name = models.CharField(max_length=50, null=True, blank=True)
    fathers_name = models.CharField(max_length=50, null=True, blank=True)
    deposit = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Balance in the moment"), default=Decimal('0'))
    reserved = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Balance in the moment"), default=Decimal('0'))
    is_active = models.BooleanField(default=False)

    @property
    def masked_number(self):
        number = self.number
        return '{}XXXXXXXX{}'.format(number[:4], number[12:16])

    class Meta:
        verbose_name = _("Card")
        verbose_name_plural = _("Cards")


class Recharges(TimeStampedModel, BaseModel, models.Model):
    card = models.ForeignKey(Cards, related_name='recharges', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Amount"))
    quote =  models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Quote"))
    deposit = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Deposit in the moment"))
    reserved = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Reserved in the moment"))

    @property
    def quote_amount(self):
        return round(self.amount * self.quote, 2)

    class Meta:
        verbose_name = _("Recharge")
        verbose_name_plural = _("Recharges")


@admin.register(Cards)
class CardsAdmin(BaseAdmin):
    readonly_fields = ['is_active']
    search_fields = ['account__user__username', 'name', 'document_1', 'document_2']
    list_display = ['account', 'number', 'name', 'document_1', 'document_2', 'birth_date', 'mothers_name', 'fathers_name', 'is_active', 'created']
