import random
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from apps.investment.models import Referrals, Comissions, Statement


def generate_loan_table(investment, borrow_amount, times=24, raw_date=False):
    rows = {'data': []}
    months = investment.remaining_months

    if times > months:
        times = months

    for i in range(1, times + 1):
        payment_date = timezone.now() + relativedelta(months=i)
        total_amount = round(borrow_amount * (1 + settings.LOAN_INTEREST_PERCENT / 100) ** i, 8)
        amount = round(total_amount / i, 8)

        if not raw_date:
            payment_date = payment_date.strftime('%d/%m/%Y')

        rows['data'].append(dict(
            times=i,
            payment_date=payment_date,
            interest_percent=round(settings.LOAN_INTEREST_PERCENT, 2),
            total_amount=f'{total_amount:.8f}',
            amount=f'{amount:.8f}'
        ))

    return rows


def generate_fixed_loan_table(investment, borrow_amount, times, raw_date=False):
    rows = {'data': []}
    months = investment.remaining_months

    if times > months:
        times = months

    for i in range(1, times + 1):
        payment_date = timezone.now() + relativedelta(months=i)
        total_amount = round(borrow_amount * (1 + investment.plan_grace_period.plan.loan_interest_percent / 100) ** times,
                             8)
        amount = round(total_amount / times, 8)

        if not raw_date:
            payment_date = payment_date.strftime('%d/%m/%Y')

        rows['data'].append(dict(
            times=i,
            payment_date=payment_date,
            interest_percent=round(investment.plan_grace_period.plan.loan_interest_percent, 2),
            total_amount=f'{total_amount:.8f}',
            amount=f'{amount:.8f}'
        ))

    return rows


def decimal_split(amount, split_times=10, min_split_amount_percent=70, max_split_amount_percent=100):
    if not isinstance(split_times, int):
        raise Exception('Split times argument must be a integer')

    splited_amount = Decimal(amount) / split_times
    split_table = []
    loop_times = split_times

    start_random = splited_amount * Decimal(min_split_amount_percent / 100)
    end_random = splited_amount * Decimal(max_split_amount_percent / 100)

    for i in range(0, loop_times):
        split_table.append(Decimal(random.uniform(float(start_random), float(end_random))))

    increment_amount = (Decimal(amount) - sum(split_table)) / split_times
    return [increment_amount + n for n in split_table]


def change_referral(user, promoter):
    referral = Referrals.objects.get(user=user)

    if  referral.promoter and referral.advisor:
        return

    comissions = Comissions.objects.filter(referral=referral)
    account = referral.promoter.accounts.filter(currency__type='investment').first()

    # Starts a transaction for not data damages
    with transaction.atomic():
        # Loop over comissions and take them from investment account of promoter
        for comission in comissions:
            account.takeout(comission.amount)
            statement = Statement.objects.filter(pk=comission.fk)
            if statement:
                statement.delete()
            comission.delete()

        # Updates the referral promoter to the correct one
        referral.promoter = promoter
        referral.save()