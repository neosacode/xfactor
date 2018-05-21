import hashlib
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exchange_core.models import Accounts, Statement
from apps.investment.models import Investments, IgnoreIncomeDays, PlanGracePeriods, Incomes


class Command(BaseCommand):
    help = 'Pay customer income'

    def handle(self, *args, **options):
        while True:
            with transaction.atomic():
                investments = Investments.objects.filter(status='paid')
                
                for investment in investments:
                    # Gera o valor do rendimento
                    if investment.plan_grace_period.payment_type == PlanGracePeriods.TYPES.daily:
                        income_amount = round(investment.amount * (investment.plan_grace_period.income_percent / Decimal('100')), 8)
                    elif investment.plan_grace_period.payment_type == PlanGracePeriods.TYPES.monthly:
                        today_income = Incomes.objects.get(date=timezone.now(), investment=investment)
                        income_amount = today_income.amount

                    # Regras validas somente para planos de investimento diarios
                    if investment.plan_grace_period.payment_type == PlanGracePeriods.TYPES.daily:
                        # O investimento so sera pago depois de 24 horas
                        if (investment.paid_date - timezone.now()).days <= 0:
                            continue

                        # Ignora os dias marcados como ignorados no sistema
                        if IgnoreIncomeDays.objects.filter(date=timezone.now().date()).exists():
                            continue

                    # Checa se não haverá duplicidade de rendimento
                    tx_bytes = '{}{}'.format(investment.pk, timezone.now().date()).encode()
                    tx_id = hashlib.sha1(tx_bytes).hexdigest()
                    statements = Statement.objects.filter(tx_id=tx_id, created__date=timezone.now().date())

                    if statements.exists():
                        continue

                    # Transfere o rendimento para a conta do investidor
                    income_account = investment.account
                    income_account.new_income(income_amount, tx_id, investment.pk)

                    print('Pagando {} para o cliente {}'.format(income_amount, income_account.user.username))
