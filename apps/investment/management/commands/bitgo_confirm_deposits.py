import hashlib
import gevent

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exchange_core.models import Accounts, Statement
from exchange_payments.gateways.bitgo import Gateway


bitgo = Gateway()


def check_transactions(account):
    print('Processando conta do usuario {}'.format(account.user.username))
    
    with transaction.atomic():
        transactions = bitgo.get_transactions(account.deposit_address)
        key_name = 'transactions'

        if not key_name in transactions:
            return

        for tx in transactions[key_name]:
            if not tx['outputs']:
                return

            if Statement.objects.filter(account=account, tx_id=tx['id']).exists():
                return

            amount = Decimal(tx['outputs'][-1]['value']) / Decimal('100000000')
            account.deposit += amount
            account.save()

            statement = Statement()
            statement.account = account
            statement.tx_id = tx['id']
            statement.amount = amount
            statement.description = 'Deposit'
            statement.type = Statement.TYPES.deposit
            statement.save()

            print("Transfering {} to {} account".format(amount, account.pk))


MAXIMUM_STACK_SIZE = 30

class Command(BaseCommand):
    help = 'Confirm bitgo transfers'

    def handle(self, *args, **options):
        offset = 0

        while True:
            accounts = Accounts.objects.filter(currency__symbol='BTC', deposit_address__isnull=False)[offset:offset + MAXIMUM_STACK_SIZE]

            gevent.wait([gevent.spawn(check_transactions, account) for account in accounts])
            offset += MAXIMUM_STACK_SIZE

            if len(accounts) < MAXIMUM_STACK_SIZE:
                offset = 0
