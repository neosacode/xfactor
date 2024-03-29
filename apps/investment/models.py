import uuid
from decimal import Decimal
from dateutil import rrule
from dateutil.relativedelta import relativedelta

from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from django.db.models import Q, Sum
from django import forms
from django.conf import settings
from model_utils.models import TimeStampedModel, StatusModel
from model_utils import Choices

from exchange_core.models import Users, Currencies, Accounts, Statement
from exchange_core.admin import BaseAdmin


def diff_month(d1, d2):
    return abs(abs(d1.year - d2.year) * 12 + d1.month - d2.month)


class Plans(TimeStampedModel, StatusModel, models.Model):
    STATUS = Choices('inactive', 'active')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    min_down = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Min down"))
    max_down = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Max down"))
    min_reinvest = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Min reinvest"), default=Decimal('0.00'))
    membership_fee = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Membership Fee"), default=Decimal('0.00'))
    promoter_comission = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Promoter Comission"), default=Decimal('0.00'))
    advisor_comission = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Advisor Comission"), default=Decimal('0.00'))
    allow_monthly_draw = models.BooleanField(default=True, verbose_name=_("Allow monthly draw"))
    order = models.IntegerField(default=0)
    # Porcentagem de limite de crédito sob o valor investido que o cliente tem direito
    overdraft_percent = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Overdraft Percent"), default=Decimal('0.00'))
    # Porcentagem de juros do limite de crédito após o vencimento da carência
    overdraft_interest_percent = models.DecimalField(max_digits=20, decimal_places=8,verbose_name=_("Overdraft interest percent"), default=Decimal('0.00'))
    # Quantidade de dias sem juros do limite de crédito
    overdraft_free_days = models.IntegerField(verbose_name=_("Overdraft Free Days"), default=0)
    # Porcentagem de empréstimo sob o valor investido que o cliente tem direito
    loan_percent = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Loan Percent"), default=Decimal('0.00'))
    # Porcentagem de juros do empréstimo após o vencimento da carência
    loan_interest_percent = models.DecimalField(max_digits=20, decimal_places=8,verbose_name=_("Loan interest percent"), default=Decimal('0.00'))

    # Porcentagem de juros do empréstimo após o vencimento da carência

    class Meta:
        verbose_name = _("Plan")
        verbose_name_plural = _("Plans")

    def __str__(self):
        return self.name


    @classmethod
    def get_by_amount(cls, amount):
        return cls.objects.filter(min_down__lte=amount, max_down__gte=amount).order_by('-max_down').first()


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
    plan = models.ForeignKey(Plans, related_name='grace_periods', verbose_name=_("Plan"), on_delete=models.CASCADE)
    grace_period = models.ForeignKey(GracePeriods, related_name='plans', verbose_name=_("Grace Period"), on_delete=models.CASCADE)
    income_percent = models.DecimalField(default=Decimal('0.00'), max_digits=20, decimal_places=8, verbose_name=_("Income percent"))
    payment_type = models.CharField(max_length=20, choices=TYPES, default=TYPES.monthly, verbose_name=_("Payment Type"),)
    currency = models.ForeignKey('exchange_core.Currencies', null=True, related_name='place_grace_periods', verbose_name=_("Currency"), on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Plan grace period")
        verbose_name_plural = _("Plan grace periods")
        unique_together = (('plan', 'grace_period', 'currency'),)
        ordering = ['grace_period__months']

    def __str__(self):
        return _("{plan} with {grace_period} months").format(plan=str(self.plan), grace_period=str(self.grace_period))


def gen_code():
    return str(uuid.uuid4().hex)[0:10]


class Investments(TimeStampedModel, models.Model):
    STATUS = Choices('paid', 'consumed', 'cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_grace_period = models.ForeignKey(PlanGracePeriods, related_name='investments', verbose_name=_("Plan grace period"), on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8, verbose_name=_("Amount"))
    membership_fee = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.00'), verbose_name=_("Membership Fee"))
    account = models.ForeignKey('exchange_core.Accounts', related_name='investments', verbose_name=_("Account"), on_delete=models.CASCADE)
    paid_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Paid Date"))
    status = models.CharField(max_length=255, choices=STATUS, default=STATUS.paid)

    def new_income(self, account, amount, tx_id, fk, date):
        # Transfere o rendimento para a conta do investidor
        account.deposit += amount
        account.save()

        # Cria o extrato do rendimento para o investidor
        statement = Statement(account_id=self.pk,
                              amount=amount, tx_id=tx_id, fk=fk)
        statement.account = account
        statement.description = 'Income'
        statement.type = Statement.TYPES.income
        statement.created = date
        statement.modified = date
        statement.save()

        return statement

    @property
    def end_date(self):
        reinvestment = self.reinvestments.filter(status='paid').first()
        if reinvestment:
            months = reinvestment.old_invest.grace_period.months
        else:
            months = self.plan_grace_period.grace_period.months
        return self.paid_date + relativedelta(months=months)

    # Retorna quantos dias faltam para vencer a carência
    @property
    def remaining_days(self):
        return (self.end_date - timezone.now()).days

    @property
    def contract_days(self):
        return (self.end_date - self.paid_date).days

    # Retorna quantos meses faltam para vencer a carência
    @property
    def remaining_months(self):
        return diff_month(timezone.now(), self.end_date)

    def __str__(self):
        return '{} - {} BTC - {}'.format(self.account.user.username, self.amount, self.plan_grace_period.plan.name)

    @classmethod
    def get_by_user(cls, user):
        return Investments.objects.filter(account__user=user).first()

    @classmethod
    def get_last_by_user(cls, user):
        return Investments.objects.filter(account__user=user).order_by('-created').first()

    @classmethod
    def get_active_by_user(cls, user):
        return Investments.objects.filter(account__user=user, status=cls.STATUS.paid).first()

    @classmethod
    def get_credit_by_user(cls, user):
        investment = cls.get_active_by_user(user)

        loan_in_use = cls.get_loan_in_use(investment)
        loan_limit = cls.get_loan_limit(investment)
        loan_available = loan_limit - loan_in_use

        overdraft_in_use = cls.get_overdraft_in_use(investment)
        overdraft_limit = cls.get_overdraft_limit(investment)
        overdraft_available = overdraft_limit - overdraft_in_use

        if investment:
            return {
                'loan': {
                    'limit': loan_limit,
                    'in_use': loan_in_use,
                    'available': loan_available
                },
                'overdraft': {
                    'limit': overdraft_limit,
                    'in_use': overdraft_in_use,
                    'available': overdraft_available,
                    'free_days': investment.plan_grace_period.plan.overdraft_free_days
                }
            }

    @classmethod
    def get_loan_limit(self, investment):
        if not investment:
            return round(Decimal('0.00'), 8)
        return investment.account.reserved * (investment.plan_grace_period.plan.loan_interest_percent / 100)

    @classmethod
    def get_loan_in_use(self, investment):
        if not investment:
            return round(Decimal('0.00'), 8)

        statements = Statement.objects.filter(type='loan', account__user=investment.account.user)
        return sum([item.amount for item in statements])

    @classmethod
    def get_overdraft_limit(self, investment):
        if not investment:
            return round(Decimal('0.00'), 8)
        return investment.account.reserved * (investment.plan_grace_period.plan.overdraft_interest_percent / 100)

    @classmethod
    def get_overdraft_in_use(self, investment):
        if not investment:
            return round(Decimal('0.00'), 8)

        statements = Statement.objects.filter(type='overdraft', account__user=investment.account.user)
        return sum([item.amount for item in statements])

    class Meta:
        verbose_name = _("Investment")
        verbose_name_plural = _("Investments")


class Incomes(models.Model):
    STATUS = Choices('created', 'paid')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    investment = models.ForeignKey(Investments, related_name='incomes', on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, default=STATUS.created)

    class Meta:
        verbose_name = _("Income")
        verbose_name_plural = _("Incomes")
        unique_together = (('investment', 'date'),)


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
        unique_together = (('user', 'type'),)

    @property
    def type_title(self):
        return 'Investment ' + self.type.title()

    @classmethod
    def get_present(cls, user):
        return Graduations.objects.filter(user=user).order_by('-created').first()


class Referrals(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('exchange_core.Users', related_name='referral', on_delete=models.CASCADE)
    promoter = models.ForeignKey('exchange_core.Users', related_name='promoter', on_delete=models.CASCADE)
    advisor = models.ForeignKey('exchange_core.Users', related_name='advisor', null=True, on_delete=models.CASCADE)

    @property
    def user_has_investments(self):
        accounts = self.user.accounts.filter(currency__type=Currencies.TYPES.investment)

        if accounts.exists():
            investment_account = accounts.first()
            return investment_account.investments.exists()

        return False



# Empréstimos
class Loans(TimeStampedModel, StatusModel, models.Model):
    STATUS = Choices('pending', 'paid')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey('exchange_core.Accounts', related_name='loans', verbose_name=_("Account"), on_delete=models.CASCADE)
    # Valor original do empréstimo
    borrowed_amount = models.DecimalField(max_digits=20, decimal_places=8)
    total_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.00'))
    # Quantidade de parcelas
    times = models.IntegerField(default=1)

    class Meta:
        verbose_name = _("Loan")
        verbose_name_plural = _("Loans")

    def __str__(self):
        return str(self.amount)


# Parcelas dos empréstimos
class Installments(TimeStampedModel, StatusModel, models.Model):
    STATUS = Choices('pending', 'paid')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Empréstimo ao qual a parcela pertence
    loan = models.ForeignKey(Loans, related_name='installments', verbose_name=_("Statement"), on_delete=models.CASCADE)
    # Numero da parcela
    order = models.IntegerField(default=1)
    # Data de vencimento da parcela
    due_date = models.DateField()
    # Porcentagem de juros da parcela
    interest_percent = models.DecimalField(max_digits=20, decimal_places=8)
    # Valor da parcela
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    # Data de recebimento da parcela
    receipt_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _("Installment")
        verbose_name_plural = _("Installments")
        ordering = ['order']

    def __str__(self):
        return str(self.amount)


# Overdrafts
class Overdrafts(TimeStampedModel, StatusModel, models.Model):
    STATUS = Choices('pending', 'paid')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey('exchange_core.Accounts', related_name='credits', verbose_name=_("Account"), on_delete=models.CASCADE)
    # Valor original do empréstimo
    borrowed_amount = models.DecimalField(max_digits=20, decimal_places=8)
    # Porcentagem de juros da parcela
    interest_percent = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.00'))
    # Data de recebimento do pagamento do crédito
    receipt_date = models.DateField(null=True, blank=True)
    # Data de vencimento
    due_date = models.DateField(null=True, blank=True)

    @property
    def remaining_days(self):
        return (self.due_date - self.created.date()).days

    class Meta:
        verbose_name = _("Credit")
        verbose_name_plural = _("Credits")
        ordering = ['-created']

    def __str__(self):
        return str(self.amount)


class Comissions(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referral = models.ForeignKey(Referrals, related_name='comissions', on_delete=models.CASCADE, null=True)
    investment = models.ForeignKey(Investments, null=True, related_name='comissions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    reinvestment = models.ForeignKey('investment.Reinvestments', related_name='comissions', on_delete=models.CASCADE, null=True)
    fk = models.UUIDField(null=True)

    class Meta:
        verbose_name = _("Comission")
        verbose_name_plural = _("Comissions")

    @classmethod
    def get_amount(self, user):
        return Comissions.objects.filter(Q(referral__promoter=user) | Q(referral__advisor=user)).aggregate(amount=Sum('amount'))['amount'] or Decimal('0.00000000')

    @classmethod
    def get_month_amount(self, user):
        return Comissions.objects.filter(Q(referral__promoter=user) | Q(referral__advisor=user)).filter(created__year=timezone.now().year, created__month=timezone.now().month).aggregate(amount=Sum('amount'))['amount'] or Decimal('0.00000000')

    @classmethod
    def get_today_amount(self, user):
        return Comissions.objects.filter(Q(referral__promoter=user) | Q(referral__advisor=user)).filter(created__date=timezone.now()).aggregate(amount=Sum('amount'))['amount'] or Decimal('0.00000000')


class Reinvestments(TimeStampedModel, models.Model):
    STATUS = Choices('paid', 'consumed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    old_invest = models.ForeignKey(PlanGracePeriods, related_name='old_invests', on_delete=models.CASCADE)
    new_invest = models.ForeignKey(PlanGracePeriods, null=True, related_name='new_invests', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    amount_before = models.DecimalField(max_digits=20, decimal_places=8)
    incomes = models.DecimalField(max_digits=20, decimal_places=8)
    membership_fee = models.DecimalField(max_digits=20, decimal_places=8)
    investment = models.ForeignKey(Investments, related_name='reinvestments', on_delete=models.CASCADE, null=True)
    status = models.CharField(max_length=30, default=STATUS.paid, choices=STATUS)

    class Meta:
        verbose_name = _("Reinvestment")
        verbose_name_plural = _("Reinvestments")

    @property
    def end_date(self):
        return self.created + relativedelta(months=self.new_invest.grace_period.months)

    # Retorna quantos dias faltam para vencer a carência
    @property
    def remaining_days(self):
        return (self.end_date - timezone.now()).days

    @property
    def contract_days(self):
        return (self.end_date - self.created).days

    # Retorna quantos meses faltam para vencer a carência
    @property
    def remaining_months(self):
        return diff_month(timezone.now(), self.end_date)


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


@admin.register(Investments)
class InvestmentsAdmin(BaseAdmin):
    list_display = ['plan_grace_period', 'account', 'created', 'status']
    ordering = ('-created',)
    readonly_fields = ['status', 'plan_grace_period', 'amount', 'account', 'paid_date']

    class Media:
        css = {'all': ('css/admin/hide-submit-buttons.css',)}

    def has_add_permission(self, request):
        return False


@admin.register(IgnoreIncomeDays)
class IgnoreIncomeDaysAdmin(BaseAdmin):
    list_display = ['date']
    ordering = ('-date',)


@admin.register(Graduations)
class GraduationsAdmin(BaseAdmin):
    list_display = ['user', 'type']
    ordering = ('-created',)


@admin.register(Incomes)
class IncomesAdmin(BaseAdmin):
    list_display = ['investment', 'amount', 'date']
    ordering = ('-created',)
    readonly_fields = ['investment']


@admin.register(Comissions)
class ComissionsAdmin(BaseAdmin):
    list_display = ['amount', 'investment', 'reinvestment', 'fk', 'created']
    ordering = ('-created',)
    readonly_fields = ['investment', 'reinvestment', 'fk', 'created']


@admin.register(Reinvestments)
class ReinvestmentsAdmin(BaseAdmin):
    list_display = ['investment', 'amount', 'old_invest', 'new_invest', 'created']
    ordering = ('-created',)
    readonly_fields = ['investment', 'amount', 'old_invest', 'new_invest']


# Cria as contas do usuário
@receiver(post_save, sender=Users, dispatch_uid='create_graduation_accounts')
def create_user_accounts(sender, instance, created, **kwargs):
    if created:
        graduation = Graduations()
        graduation.user = instance
        graduation.type = Graduations._promoter
        graduation.save()