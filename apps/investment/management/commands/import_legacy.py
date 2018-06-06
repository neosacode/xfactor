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
from apps.investment.models import Investments, PlanGracePeriods, Referrals, Incomes, Comissions, Plans, Graduations

class Command(BaseCommand):
    help = 'Import Legacy Data'

    def handle(self, *args, **options):
        # # Migracao de usuarios
        # Users.objects.all().delete()
        # Accounts.objects.all().delete()

        # with open('/app/apps/investment/management/commands/data/users.csv', 'r') as f:
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

        with open('apps/investment/management/commands/data/users.csv', 'r') as f:
            reader = csv.DictReader(f)
            bulk_users = []
            bulk_accounts = []
            n = 1

            currencies = Currencies.objects.all()

            for row in reader:
                try:
                    account = Accounts.objects.get(user__username=row['username'], currency__type='investment')
                    account.deposit = Decimal(row['balance'])
                    account.save()

                    print('Atualizando saldo o usuáro {}'.format(row['username']))
                except:
                    print('Usuario {} nao encontrado'.format(row['username']))

        # Migracao de cobrancas
        # Investments.objects.all().delete()

        # with open('/app/apps/investment/management/commands/data/investments.csv', 'r') as f:
        #     reader = csv.DictReader(f)
            
        #     for row in reader:
        #         print(row['username'], row['paid_date'])
                # investment = Investments.objects.get(account__user__username=row['username'])
                # investment.paid_date = 
                
                # print('Processando investimento de {} para o usuáro {}'.format(investment.amount, row['username']))

            # Investments.objects.bulk_create(bulk_investments)
            # print('Gravando investimentos no banco')


        # Referrals.objects.all().delete()

        # # Migracao de indicacoes
        # with open('/app/apps/investment/management/commands/data/referrals.csv', 'r') as f:
        #     reader = csv.DictReader(f)
        #     bulk_referrals = []

        #     for row in reader:
        #         referral = Referrals()
        #         referral.promoter = Users.objects.get(username=row['promoter'])
        #         referral.user = Users.objects.get(username=row['username'])

        #         bulk_referrals.append(referral)

        #         print('Processando usuáro {} com promoter {}'.format(row['username'], row['promoter']))

        #     Referrals.objects.bulk_create(bulk_referrals)
        #     print('Gravando referencias no banco')
                

        # Statement.objects.filter(created__date__lt=datetime(2018, 5, 28)).delete()
        # Incomes.objects.all().delete()

        # # Migracao de relatorio de rendimentos
        # with open('/app/apps/investment/management/commands/data/incomes.csv', 'r') as f:
        #     reader = csv.DictReader(f)
        #     bulk_statements = []
        #     bulk_incomes = []
        #     accounts = {}
        #     investments = {}

        #     for row in reader:
        #         if not row['username'] in accounts:
        #             accounts[row['username']] = Accounts.objects.get(currency__type=Currencies.TYPES.investment, user__username=row['username'])

        #         if not row['username'] in investments:
        #             investments[row['username']] = Investments.objects.get(account__user__username=row['username'])

        #         statement = Statement()
        #         statement.account = accounts[row['username']]
        #         statement.amount = Decimal(row['value'])
        #         statement.description = row['description']
        #         statement.created = row['created']
        #         statement.modified = row['created']
        #         statement.type = row['type']

        #         if row['type'] == 'income':
        #             income = Incomes()
        #             income.date = dateutil.parser.parse(row['created'])
        #             income.amount = statement.amount
        #             income.investment = investments[row['username']]
        #             bulk_incomes.append(income)
        #         bulk_statements.append(statement)

        #         print('Processando extrato {} com valor de {} para a conta de investimentos do usuáro {}'.format(statement.description, statement.amount, row['username']))

        #     Statement.objects.bulk_create(bulk_statements)
        #     Incomes.objects.bulk_create(bulk_incomes)
        #     print('Gravando rendimentos no banco')


        # Statement.objects.filter(type='comission').delete()

        # with open('/app/apps/investment/management/commands/data/comissions.csv', 'r') as f:
        #     reader = csv.DictReader(f)
        #     comissions_bulk = []

        #     for row in reader:
        #         referral = Referrals.objects.get(promoter=Users.objects.get(username=row['sponsor']), user=Users.objects.get(username=row['username']))

        #         comission = Comissions()
        #         comission.referral = referral
        #         comission.amount = Decimal(row['value'])
        #         comission.created = dateutil.parser.parse(row['created'])
        #         comission.modified = dateutil.parser.parse(row['created'])
        #         comission.plan = Plans.objects.get(name__iexact=row['plan'])

        #         comissions_bulk.append(comission)

        #         print(row)

        #     Comissions.objects.bulk_create(comissions_bulk)

        #     print('Gravando comissoes')


        # for user in Users.objects.all():
        #     graduations_bulk = []
        #     Comissions.objects.filter(referral__promoter=user).update(graduation=Graduations.get_present(user))


        # # Migracao de relatorio de rendimentos
        # Statement.objects.filter(type='income').delete()

        # with open('/app/apps/investment/management/commands/data/incomes.csv', 'r') as f:
        #     reader = csv.DictReader(f)
            
        #     for row in reader:
        #         statement = Statement()
        #         statement.account = Accounts.objects.get(user__username=row['username'], currency__type='investment')
        #         statement.amount = Decimal(row['value'])
        #         statement.description = 'Income of the day'
        #         statement.created = dateutil.parser.parse(row['created'])
        #         statement.modified = dateutil.parser.parse(row['created'])
        #         statement.type = 'income'
        #         statement.save()

        #         print('Income for user {} in date {}'.format(statement.account.user.username, statement.created))
        