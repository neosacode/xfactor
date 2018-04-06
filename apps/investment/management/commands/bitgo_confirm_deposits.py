import hashlib
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exchange_core.models import Accounts, Statement
from exchange_payments.gateways.bitgo import Gateway

class Command(BaseCommand):
    help = 'Confirm bitgo transfers'

    def handle(self, *args, **options):
        bitgo = Gateway()

        while True:
            with transaction.atomic():
                for account in Accounts.objects.filter(currency__symbol='BTC', deposit_address__isnull=False):
                    transactions = bitgo.get_transactions(account.deposit_address)
                    key_name = 'transactions'

                    if not key_name in transactions:
                        continue

                    for tx in transactions[key_name]:
                        if not tx['outputs']:
                            continue

                        if Statement.objects.filter(account=account, tx_id=tx['id']).exists():
                            continue

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
