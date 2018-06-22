from decimal import Decimal
from django.db import transaction

from django.core.management.base import BaseCommand
from exchange_core.models import Accounts, Statement, Currencies
from apps.investment.models import Investments, Reinvestments


STATEMENT_TYPE = 'investment_plan_termination'


class Command(BaseCommand):
    help = 'Auto withdraw investments and reinvestiments when investment plan grace period ends'

    def handle(self, *args, **options):
        while True:
            for item in Investments.objects.order_by('created'):
                with transaction.atomic():
                    reinvestments = Reinvestments.objects.filter(investment=item)

                    # Skip when investment has reinvestiments
                    if reinvestments.exists():
                        continue

                    # Skip if investment grace period not ends yet
                    if not item.remaining_days <= 0:
                        continue

                    if Statement.objects.filter(type=STATEMENT_TYPE, fk=item.pk).exists():
                        continue

                    account = item.account
                    withdraw_fee = item.account.currency.withdraw_fee
                    withdraw_fixed_fee = item.account.currency.withdraw_fixed_fee
                    total_amount = account.deposit + account.reserved
                    discount = (total_amount * (withdraw_fee / 100)) + withdraw_fixed_fee
                    pay_amount = total_amount - discount

                    account.deposit = 0
                    account.reserved = 0
                    account.save()

                    checking_account = Accounts.objects.filter(user=account.user, currency__type=Currencies.TYPES.checking).first()
                    checking_account.to_deposit(pay_amount)

                    statement = Statement()
                    statement.amount = Decimal('0') - total_amount
                    statement.description = 'Termination of investment plan'
                    statement.type = STATEMENT_TYPE
                    statement.account = account
                    statement.fk = item.pk
                    statement.save()

                    statement = Statement()
                    statement.amount = pay_amount
                    statement.description = 'Termination of investment plan'
                    statement.type = STATEMENT_TYPE
                    statement.account = checking_account
                    statement.fk = item.pk
                    statement.save()

                    print(total_amount)
                    print('Auto withdraw reinvestment of {} from {} user'.format(item.amount, item.account.user.username))
