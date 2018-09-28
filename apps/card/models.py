from decimal import Decimal
from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from templated_email import send_templated_mail
from model_utils.models import TimeStampedModel
from exchange_core.models import BaseModel
from exchange_core.admin import BaseAdmin


class Cards(TimeStampedModel, BaseModel, models.Model):
    account = models.ForeignKey('exchange_core.Accounts', related_name='cards', on_delete=models.CASCADE, verbose_name=_("Account"))
    number = models.CharField(max_length=16, unique=True, verbose_name=_("Number"))
    name = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Name"))
    document_1 = models.CharField(max_length=30, null=True, blank=True, verbose_name=_("Document 1"))
    document_2 = models.CharField(max_length=30, null=True, blank=True, verbose_name=_("Document 2"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("Birth date"))
    mothers_name = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Mothers name"))
    fathers_name = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Fathers name"))
    deposit = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Deposit"), default=Decimal('0'))
    reserved = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Reserved"), default=Decimal('0'))
    is_active = models.BooleanField(default=False, verbose_name=_("Is active"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_is_active = self.is_active

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
    is_paid = models.BooleanField(default=False, verbose_name=_("Is paid"), help_text=_("Mark this if the rechard has been paid"))

    @property
    def quote_amount(self):
        return round(self.amount * self.quote, 2)

    class Meta:
        verbose_name = _("Recharge")
        verbose_name_plural = _("Recharges")


@admin.register(Cards)
class CardsAdmin(BaseAdmin):
    search_fields = ['account__user__username', 'name', 'document_1', 'document_2']
    list_display = ['account', 'number', 'name', 'document_1', 'document_2', 'birth_date', 'mothers_name', 'fathers_name', 'is_active', 'created']


@receiver(post_save, sender=Cards, dispatch_uid='save_card')
def create_currency_user_accounts(sender, instance, created, **kwargs):
    if instance.is_active is not instance.initial_is_active and instance.is_active is True:
        send_templated_mail(
            template_name='card_approved.email',
            from_email=settings.DEFAULT_FROM_EMAIL,
            context={'user': instance.account.user},
            recipient_list=[instance.account.user.email]
        )
