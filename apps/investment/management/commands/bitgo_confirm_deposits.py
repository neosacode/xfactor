import time
import gevent

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from exchange_core.models import Accounts, Statement
from exchange_payments.gateways.bitgo import Gateway


bitgo = Gateway()


def check_transaction(output):
    with transaction.atomic():
        accounts = Accounts.objects.filter(deposit_address=output['address'])

        if not accounts.exists():
            return

        account = accounts.first()
        print('Processando conta do usuario {}'.format(account.user.username))

        if Statement.objects.filter(account=account, tx_id=output['id']).exists():
            return

        satoshis = Decimal(output['value'])

        if satoshis < 0:
            return

        amount = satoshis / Decimal('100000000')
        account.deposit += amount
        account.save()

        statement = Statement()
        statement.account = account
        statement.tx_id = output['id']
        statement.amount = amount
        statement.description = 'Deposit'
        statement.type = Statement.TYPES.deposit
        statement.save()

        print("Transfering {} to {} account".format(amount, account.pk))


MAXIMUM_STACK_SIZE = 30

class Command(BaseCommand):
    help = 'Confirm bitgo transfers'

    def handle(self, *args, **options):
        while True:
            wallets = bitgo.get_wallets()

            for wallet in wallets['wallets']:
                transactions = bitgo.get_transactions(wallet['id'])

                for transfer in transactions['transfers']:
                    gevent.wait([gevent.spawn(check_transaction, output) for output in transfer['outputs']])

            time.sleep(30)
