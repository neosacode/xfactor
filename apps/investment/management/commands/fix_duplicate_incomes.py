from decimal import Decimal

from datetime import datetime, timedelta
from dateutil.rrule import rrule, DAILY
from apps.investment.utils import decimal_split

from django.core.management.base import BaseCommand
from apps.investment.models import Investments, Incomes


class Command(BaseCommand):
    help = 'Pay customer income'

    def handle(self, *args, **options):
        bulk_incomes = []

        for item in Investments.objects.filter(created__date=datetime(2018, 5, 27)):
            start_date = datetime(2018, 5, 29)
            days = (item.end_date - start_date).days
            end_date = start_date + timedelta(days=days)
            range_dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
            grace_period = item.plan_grace_period
            discount = round((item.amount * (grace_period.income_percent / Decimal('100'))) / Decimal('30'), 8) * (datetime(2018, 5, 29) - item.paid_date).days
            income_amount = round((item.amount * (grace_period.income_percent / 100)) * grace_period.grace_period.months, 8) - discount
            income_table = decimal_split(income_amount, len(range_dates), 98, 100)

            date_index = 0

            for dt in range_dates:
                income = Incomes()
                income.date = dt
                income.amount = income_table[date_index]
                income.investment = item
                bulk_incomes.append(income)

                print('Processando data {}'.format(dt))

                date_index += 1

        Incomes.objects.bulk_create(bulk_incomes)
