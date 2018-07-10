import hashlib

from decimal import Decimal
from collections import defaultdict
from pprint import pprint

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction

from exchange_core.models import Statement
from apps.investment.models import Investments, Plans, Referrals, Comissions, Accounts, Graduations


LINE_1_LIMIT = 15
LINE_2_LIMIT = 75
LINE_3_LIMIT = 375


def get_descents(users, limit):
    referrals = Referrals.objects.select_related('user').filter(promoter__in=users)
    descents = []

    for referral in referrals:
        investment = Investments.get_active_by_user(referral.user)

        if len(descents) >= limit:
            break

        if investment:
            descents.append(investment.account.user)

    return descents


class Command(BaseCommand):
    help = 'Pay profit sharing'

    def handle(self, *args, **options):
        while True:
            advisors = Graduations.objects.select_related('user').filter(type=Graduations._advisor).order_by('user__created')
            savings = Plans.objects.get(name__iexact='savings')

            for advisor in advisors:
                if advisor.user.username != 'diego_americo':
                    continue

                investment = Investments.get_active_by_user(advisor.user)

                if not investment:
                    continue

                _1 = get_descents([advisor.user], LINE_1_LIMIT)
                _2 = get_descents(_1, LINE_2_LIMIT)
                _3 = get_descents(_2, LINE_3_LIMIT)
                
                comission_amount = len(_1 + _2 + _3) * savings.membership_fee

                with transaction.atomic():
                    investment_account = Accounts.objects.get(user=advisor.user, currency__type='investment')

                    if Statement.objects.filter(account=investment_account, type='profit_sharing_bonus').exists():
                        print('Already paid')
                        continue

                    investment_account.to_deposit(comission_amount)

                    s = Statement()
                    s.account = investment_account
                    s.amount = comission_amount
                    s.description = 'Profit sharing bonus'
                    s.type = 'profit_sharing_bonus'
                    s.save()

                    comission = Comissions()
                    comission.amount = comission_amount
                    comission.investment = investment
                    comission.fk = s.pk
                    comission.save()

                    print('Paying {} of profit sharing to {}'.format(comission_amount, advisor.user.username))

