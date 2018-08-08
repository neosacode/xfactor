from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from exchange_core.models import Statement
from apps.investment.models import Investments, Plans, Referrals, Comissions, Accounts, Graduations


LINE_1_LIMIT = 15
LINE_2_LIMIT = 75
LINE_3_LIMIT = 375

date_kwargs = {'created__date__lte': datetime(2018, 7, 10)}


def get_descents(users, limit):
    referrals = Referrals.objects.select_related('user').filter(promoter__in=users, **date_kwargs)
    descents = []

    for referral in referrals:
        investment = Investments.get_last_by_user(referral.user)

        if len(descents) >= limit:
            break

        if investment:
            descents.append(investment.account.user)

    return descents


class Command(BaseCommand):
    help = 'Pay profit sharing'

    def handle(self, *args, **options):
        while True:
            with transaction.atomic():
                advisors = Graduations.objects.select_related('user').filter(type=Graduations._advisor).order_by('user__created')
                savings = Plans.objects.get(name__iexact='savings')

                for advisor in advisors:
                    referral_advisors = Statement.objects.filter(type__in=['course_subscription', 'advisor_card_request'], account__user__referral__promoter=advisor.user).count()
                    investment = Investments.get_active_by_user(advisor.user)

                    if referral_advisors < 5:
                        continue

                    if not investment:
                        continue

                    _1 = get_descents([advisor.user], LINE_1_LIMIT)
                    _2 = get_descents(_1, LINE_2_LIMIT)
                    _3 = get_descents(_2, LINE_3_LIMIT)

                    comission_amount = len(_1 + _2 + _3) * savings.membership_fee

                        investment_account = Accounts.objects.get(user=advisor.user, currency__type='investment')
                        items = Statement.objects.filter(account=investment_account, type='profit_sharing_bonus', **date_kwargs)
                        discount = Decimal('0')

                        for item in items:
                            discount += item.amount

                        comission_amount -= discount

                        if comission_amount <= Decimal('0'):
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

                raise Exception('iasjdaisjdiasd')


