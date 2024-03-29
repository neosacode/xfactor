import hashlib

from django.utils import timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from exchange_core.models import Statement
from apps.investment.models import Investments, Incomes


class Command(BaseCommand):
    help = 'Pay customer income'

    def handle(self, *args, **options):
        while True:
            incomes = Incomes.objects.filter(date__lte=timezone.now(), status=Incomes.STATUS.created, investment__status=Investments.STATUS.paid).order_by('-date')
            
            for income in incomes:
                with transaction.atomic():
                    investment = income.investment
                    # Checa se não haverá duplicidade de rendimento
                    tx_bytes = '{}{}'.format(investment.pk, income.date).encode()
                    tx_id = hashlib.sha1(tx_bytes).hexdigest()
                    statements = Statement.objects.filter(tx_id=tx_id)

                    income.status = Incomes.STATUS.paid
                    income.save()

                    if statements.exists():
                        continue

                    # Transfere o rendimento para a conta do investidor
                    investment.new_income(investment.account, income.amount, tx_id, investment.pk, income.date)

                    print('Paying {} for the customer {} in date {}'.format(income.amount, investment.account.user.username, income.date))
