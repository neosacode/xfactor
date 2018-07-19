from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from exchange_core.models import BaseModel
from exchange_core.admin import BaseAdmin


class Cards(TimeStampedModel, BaseModel, models.Model):
    account = models.ForeignKey('exchange_core.Accounts', related_name='cards', on_delete=models.CASCADE)
    number = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=50)
    document_1 = models.CharField(max_length=30, null=True)
    document_2 = models.CharField(max_length=30, null=True)
    birth_date = models.DateField(null=True)
    mothers_name = models.CharField(max_length=50, null=True)
    fathers_name = models.CharField(max_length=50, null=True)
    is_active = models.BooleanField(default=False)

    @property
    def masked_number(self):
        number = self.number
        return '{}XXXXXXXX{}'.format(number[:4], number[12:16])

    class Meta:
        verbose_name = _("Card")
        verbose_name_plural = _("Cards")


@admin.register(Cards)
class CardsAdmin(BaseAdmin):
    readonly_fields = ['is_active']
    search_fields = ['account__user__username', 'name', 'document_1', 'document_2']
    list_display = ['account', 'number', 'name', 'document_1', 'document_2', 'birth_date', 'mothers_name', 'fathers_name', 'is_active', 'created']
