from decimal import Decimal
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from exchange_core.models import Statement
from apps.investment.models import Referrals, Comissions, Accounts, Graduations


def pay_course_comissions():
    statement = Statement.objects.filter(type__in=['course_subscription', 'advisor_card_request']).order_by('created')
    payment_month = None
    ledger = defaultdict(lambda: 0)

    for item in statement:
        user = item.account.user
        referral = Referrals.objects.get(user=user)
        promoter = referral.promoter
        graduation = Graduations.get_present(promoter)
        month = '{}-{}'.format(item.created.month, item.created.year)

        if graduation.type == Graduations._advisor:
            advisor = referral.promoter
        else:
            advisor = referral.advisor

        # If user doesn't has a advisor, skip
        if not advisor:
            continue

        if not payment_month:
            payment_month = month

        if month != payment_month and item.created.day >= 10:
            payment_month = month
            ledger = defaultdict(lambda: 0)

        ledger[advisor.username] += 1

        if ledger[advisor.username] >= 1 and ledger[advisor.username] <= 4:
            comission_amount = abs(item.amount) * Decimal('0.1')
        elif ledger[advisor.username] >= 5 and ledger[advisor.username] <= 10:
            comission_amount = abs(item.amount)
        elif ledger[advisor.username] >= 11:
            comission_amount = abs(item.amount) * Decimal('0.1')

        # Skip if comission is already paid
        if Comissions.objects.filter(fk=item.pk).exists():
            continue

        with transaction.atomic():
            # Pay the comission
            comission = Comissions()
            comission.referral = referral
            comission.amount = comission_amount
            comission.fk = item.pk
            comission.save()

            investment_account = Accounts.objects.filter(user=advisor, currency__type='investment').first()
            investment_account.to_deposit(comission_amount)

            print('Paying {} comission to {} from {} advisor course'.format(comission_amount, advisor.username,
                                                                            user.username))


class Command(BaseCommand):
    help = 'Pay course comission'

    def handle(self, *args, **options):
        while True:
            pay_course_comissions()