import hashlib
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exchange_core.models import Accounts, Statement
from apps.investment.models import Charges, IgnoreIncomeDays, PlanGracePeriods


class Command(BaseCommand):
    help = 'Pay customer income'

    def handle(self, *args, **options):
        while True:
            with transaction.atomic():
                charges = Charges.objects.filter(status='paid')

                for charge in charges:
                    # Gera o valor do rendimento
                    if charge.plan_grace_period.payment_type == PlanGracePeriods.TYPES.daily:
                        income_amount = round(charge.amount * (charge.plan_grace_period.income_percent / Decimal('100')), 8)
                    elif charge.plan_grace_period.payment_type == PlanGracePeriods.TYPES.monthly:
                        

                    # O investimento so sera pago depois de 24 horas
                    if (charge.paid_date - timezone.now()).days <= 0:
                        continue

                    # Ignora os dias marcados como ignorados no sistema
                    if IgnoreIncomeDays.objects.filter(date=timezone.now().date()).exists():
                        continue

                    # Checa se não haverá duplicidade de rendimento
                    tx_bytes = '{}{}'.format(charge.pk, timezone.now().date()).encode()
                    tx_id = hashlib.sha1(tx_bytes).hexdigest()
                    statements = Statement.objects.filter(tx_id=tx_id, created__date=timezone.now().date())

                    if statements.exists():
                        continue

                    # Transfere o rendimento para a conta do investidor
                    currency_account = charge.account
                    currency_account.deposit += income_amount
                    currency_account.save()

                    # Cria o extrato do rendimento para o investidor
                    statement = Statement()
                    statement.account = currency_account
                    statement.amount = income_amount
                    statement.description = 'Income'
                    statement.type = Statement.TYPES.income
                    statement.tx_id = tx_id
                    statement.fk = charge.pk
                    statement.save()

                    print('Pagando {} para o cliente {}'.format(income_amount, currency_account.user.username))
