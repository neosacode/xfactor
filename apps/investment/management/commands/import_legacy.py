import hashlib
import csv
import dateutil.parser

from datetime import date, datetime, timedelta
from dateutil.rrule import rrule, DAILY
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exchange_core.models import Users, Accounts, Statement, Currencies
from exchange_payments.gateways.bitgo import Gateway
from apps.investment.utils import decimal_split
from apps.investment.models import Investments, PlanGracePeriods, Referrals, Incomes

class Command(BaseCommand):
    help = 'Import Legacy Data'

    def handle(self, *args, **options):
        # # Migracao de usuarios
        # Users.objects.all().delete()
        # Accounts.objects.all().delete()

        # with open('/home/juliano/work/new-xfactor/apps/investment/management/commands/data/users.csv', 'r') as f:
        #     reader = csv.DictReader(f)
        #     bulk_users = []
        #     bulk_accounts = []
        #     n = 1

        #     currencies = Currencies.objects.all()

        #     for row in reader:
        #         user = Users()
        #         user.username = row['username']
        #         user.first_name = row['first_name']
        #         user.last_name = row['last_name']
        #         user.email = row['email']
        #         user.password = row['password']
        #         user.created = row['created']
        #         user.modified = row['modified']
        #         user.is_active = True

        #         bulk_users.append(user)

        #         for currency in currencies:
        #             account = Accounts()
        #             account.user = user
        #             account.currency = currency

        #             bulk_accounts.append(account)

        #         print(n, ' - Processando usuário ', user.username)
        #         n += 1

        #     Users.objects.bulk_create(bulk_users)
        #     Accounts.objects.bulk_create(bulk_accounts)
        #     print('Gravando usuários no banco')

        # with open('/home/juliano/work/new-xfactor/apps/investment/management/commands/data/users.csv', 'r') as f:
        #     reader = csv.DictReader(f)
        #     bulk_users = []
        #     bulk_accounts = []
        #     n = 1

        #     currencies = Currencies.objects.all()

        #     for row in reader:
        #         account = Accounts.objects.get(user__username=row['username'], currency__type='investment')
        #         account.deposit = Decimal(row['balance'])
        #         account.save()

        #         print('Atualizando saldo o usuáro {}'.format(row['username']))

        # Migracao de cobrancas
        Investments.objects.all().delete()

        with open('/home/juliano/work/new-xfactor/apps/investment/management/commands/data/investments.csv', 'r') as f:
            reader = csv.DictReader(f)
            accounts = Accounts.objects.filter(user__username__in=[row['username'] for row in reader], currency__type=Currencies.TYPES.investment)
            accounts_pk = {account.user.username: account.pk for account in accounts}
            bulk_investments = []

            f.seek(0)
            reader = csv.DictReader(f)
            
            for row in reader:
                investment = Investments()
                investment.account_id = accounts_pk[row['username']]
                investment.membership_fee = Decimal(row['membership_fee'])
                investment.amount = Decimal(row['amount'])
                investment.paid_date = row['paid_date']
                investment.created = row['created']
                investment.modified = row['modified']
                investment.plan_grace_period = PlanGracePeriods.objects.get(plan__name__iexact=row['name'], grace_period__months=row['months'])

                account = investment.account
                account.reserved = investment.amount
                account.save()

                bulk_investments.append(investment)
                print('Processando investimento de {} para o usuáro {}'.format(investment.amount, row['username']))

            Investments.objects.bulk_create(bulk_investments)
            print('Gravando investimentos no banco')


        Referrals.objects.all().delete()

        # Migracao de indicacoes
        with open('/home/juliano/work/new-xfactor/apps/investment/management/commands/data/referrals.csv', 'r') as f:
            reader = csv.DictReader(f)
            bulk_referrals = []

            for row in reader:
                referral = Referrals()
                referral.promoter = Users.objects.get(username=row['promoter'])
                referral.user = Users.objects.get(username=row['username'])

                bulk_referrals.append(referral)

                print('Processando usuáro {} com promoter {}'.format(row['username'], row['promoter']))

            Referrals.objects.bulk_create(bulk_referrals)
            print('Gravando referencias no banco')
                

        Statement.objects.all().delete()
        Incomes.objects.all().delete()

        # Migracao de relatorio de rendimentos
        with open('/home/juliano/work/new-xfactor/apps/investment/management/commands/data/incomes.csv', 'r') as f:
            reader = csv.DictReader(f)
            bulk_statements = []
            bulk_incomes = []
            accounts = {}
            investments = {}

            for row in reader:
                if not row['username'] in accounts:
                    accounts[row['username']] = Accounts.objects.get(currency__type=Currencies.TYPES.investment, user__username=row['username'])

                if not row['username'] in investments:
                    investments[row['username']] = Investments.objects.get(account__user__username=row['username'])

                statement = Statement()
                statement.account = accounts[row['username']]
                statement.amount = Decimal(row['value'])
                statement.description = row['description']
                statement.created = row['created']
                statement.modified = row['created']
                statement.type = row['type']

                income = Incomes()
                income.date = dateutil.parser.parse(row['created'])
                income.amount = statement.amount
                income.investment = investments[row['username']]

                bulk_statements.append(statement)
                bulk_incomes.append(income)
                print('Processando extrato {} com valor de {} para a conta de investimentos do usuáro {}'.format(statement.description, statement.amount, row['username']))

            Statement.objects.bulk_create(bulk_statements)
            Incomes.objects.bulk_create(bulk_incomes)
            print('Gravando rendimentos no banco')