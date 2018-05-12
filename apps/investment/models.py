import uuid
from decimal import Decimal

from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django import forms
from model_utils.models import TimeStampedModel, StatusModel
from model_utils import Choices

from exchange_core.models import Users, Currencies, Accounts
from exchange_core.admin import BaseAdmin


class Plans(TimeStampedModel, StatusModel, models.Model):
    STATUS = Choices('inactive', 'active')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    min_down = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Min down"))
    max_down = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Max down"))
    min_reinvest = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Min reinvest"), default=Decimal('0.00'))
    allow_monthly_draw = models.BooleanField(default=True, verbose_name=_("Allow monthly draw"))
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = _("Plan")
        verbose_name_plural = _("Plans")

    def __str__(self):
        return self.name


class GracePeriods(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    months = models.IntegerField(verbose_name=_("Months"), unique=True)

    class Meta:
        verbose_name = _("Grace period")
        verbose_name_plural = _("Grace periods")

    def __str__(self):
        return str(self.months)


class PlanGracePeriods(TimeStampedModel, StatusModel, models.Model):
    STATUS = Choices('inactive', 'active')
    TYPES = Choices('daily', 'monthly')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plans, related_name='grace_periods', on_delete=models.CASCADE)
    grace_period = models.ForeignKey(GracePeriods, related_name='plans', on_delete=models.CASCADE)
    income_percent = models.DecimalField(default=Decimal('0.00'), max_digits=20, decimal_places=8, verbose_name=_("Income percent"))
    membership_fee = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Membership fee")),
    payment_type = models.CharField(max_length=20, choices=TYPES, default=TYPES.monthly)
    currency = models.ForeignKey('exchange_core.Currencies', null=True, related_name='place_grace_periods', verbose_name=_("Currency"), on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Plan grace period")
        verbose_name_plural = _("Plan grace periods")
        unique_together = (('plan', 'grace_period', 'currency'),)
        ordering = ['grace_period__months']

    def __str__(self):
        return str(self.plan) + ' with ' + str(self.grace_period) + ' months'


def gen_code():
    return str(uuid.uuid4().hex)[0:10]


class Charges(TimeStampedModel, StatusModel, models.Model):
    STATUS = Choices('pending', 'paid', 'consumed', 'cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_grace_period = models.ForeignKey(PlanGracePeriods, related_name='charges', verbose_name=_("Plan grace period"), on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    account = models.ForeignKey('exchange_core.Accounts', related_name='statement_chages', on_delete=models.CASCADE)
    code = models.CharField(max_length=10, default=gen_code)
    paid_date = models.DateTimeField(null=True, blank=True)

    @property
    def end_date(self):
        return self.paid_date + relativedelta(months=self.plan_grace_period.grace_period.months)

    # Retorna quantos dias faltam para vencer a carência
    @property
    def remaining_days(self):
        return (self.end_date - timezone.now()).days

    # Retorna quantos meses faltam para vencer a carência
    @property
    def remaining_months(self):
        return round(self.remaining_days / 30)

    def __str__(self):
        return str(self.amount)

    class Meta:
        verbose_name = _("Charge")
        verbose_name_plural = _("Charges")


class Incomes(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    charge = models.ForeignKey(Charges, related_name='incomes', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Income")
        verbose_name_plural = _("Incomes")


class IgnoreIncomeDays(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(verbose_name=_("Date to be ignored"), unique=True)

    class Meta:
        verbose_name = _("Ignore income date")
        verbose_name_plural = _("Ignore income dates")

    def __str__(self):
        return str(self.date)


class Graduations(models.Model):
    _promoter = 'promoter'
    _advisor = 'advisor'

    TYPES = ((_promoter, _('Investment Promoter')), (_advisor, _('Investment Advisor')),)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('exchange_core.Users', related_name='graduations', on_delete=models.CASCADE)
    type = models.CharField(max_length=30, choices=TYPES)

    class Meta:
        verbose_name = _("Graduation")
        verbose_name_plural = _("Graduations")

    @classmethod
    def get_present(cls, user):
        return Graduations.objects.filter(user=user).order_by('-created').first()


class Referrals(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('exchange_core.Users', related_name='referral', on_delete=models.CASCADE)
    promoter = models.ForeignKey('exchange_core.Users', related_name='promoter', on_delete=models.CASCADE)
    advisor = models.ForeignKey('exchange_core.Users', related_name='advisor', null=True, on_delete=models.CASCADE)


class PlanGracePeriodForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].queryset = Currencies.objects.filter(type=Currencies.TYPES.investment)


@admin.register(Plans)
class PlansAdmin(BaseAdmin):
    list_display = ['name', 'min_down', 'max_down', 'allow_monthly_draw', 'status',
                    'created']
    ordering = ('-created',)


@admin.register(GracePeriods)
class GracePeriodsAdmin(BaseAdmin):
    list_display = ['months']
    ordering = ('-created',)


@admin.register(PlanGracePeriods)
class PlanGracePeriodsAdmin(BaseAdmin):
    list_display = ['plan', 'grace_period', 'income_percent', 'status']
    ordering = ('-created',)
    form = PlanGracePeriodForm
    save_as = True


@admin.register(Charges)
class ChargesAdmin(BaseAdmin):
    list_display = ['plan_grace_period', 'account', 'created', 'status']
    ordering = ('-created',)


@admin.register(IgnoreIncomeDays)
class IgnoreIncomeDaysAdmin(BaseAdmin):
    list_display = ['date']
    ordering = ('-date',)

@admin.register(Graduations)
class GraduationsAdmin(BaseAdmin):
    list_display = ['user', 'type']
    ordering = ('-created',)


# Cria as contas do usuário
@receiver(post_save, sender=Users, dispatch_uid='create_graduation_accounts')
def create_user_accounts(sender, instance, created, **kwargs):
    if created:
        graduation = Graduations()
        graduation.user = instance
        graduation.type = Graduations._promoter
        graduation.save()