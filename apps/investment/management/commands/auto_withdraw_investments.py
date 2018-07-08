from decimal import Decimal
from datetime import timedelta
from dateutil.rrule import rrule, DAILY
from django.db import transaction

from django.core.management.base import BaseCommand
from django.utils import timezone
from exchange_core.models import Accounts, Statement, Currencies
from apps.investment.models import Investments, Reinvestments, Plans, PlanGracePeriods, Incomes
from apps.investment.utils import decimal_split


STATEMENT_TYPE = 'investment_plan_termination'
STATEMENT_TYPE_RETURN = 'return_of_invested_amount'


def withdraw_investments():
    for item in Investments.objects.order_by('paid_date'):
        with transaction.atomic():
            reinvestments_qs = Reinvestments.objects.filter(investment=item, status=Reinvestments.STATUS.paid).order_by('created')
            reinvestment = reinvestments_qs.first()
            main_investment_was_paid = Statement.objects.filter(fk=item.pk, type=STATEMENT_TYPE).exists()
            remaining_days = item.remaining_days

            foreign_key = item.pk
            message_amount = item.amount

            if not reinvestment and item.status == Investments.STATUS.consumed:
                continue

            if reinvestment and main_investment_was_paid:
                remaining_days = reinvestment.remaining_days
                foreign_key = reinvestment.pk

            if Statement.objects.filter(type=foreign_key).exists():
                continue

            # Skip if investment grace period not ends yet
            if not remaining_days <= 0:
                continue

            account = item.account
            withdraw_fee = item.account.currency.withdraw_fee
            withdraw_fixed_fee = item.account.currency.withdraw_fixed_fee

            total_amount = account.deposit + account.reserved
            reserved = 0

            if reinvestment:
                if main_investment_was_paid:
                    message_amount = reinvestment.amount
                    reserved = account.reserved - reinvestment.amount
                    total_amount = total_amount - reserved

                    reinvestment.status = Reinvestments.STATUS.consumed
                    reinvestment.save()
                else:
                    message_amount = reinvestment.amount_before
                    reserved = account.reserved - reinvestment.amount_before
                    total_amount = total_amount - reserved

            discount = (total_amount * (withdraw_fee / 100)) + withdraw_fixed_fee
            pay_amount = total_amount - discount

            account.deposit = 0
            account.reserved = reserved
            account.save()

            checking_account = Accounts.objects.filter(user=account.user, currency__type=Currencies.TYPES.checking).first()
            checking_account.to_deposit(pay_amount)

            statement = Statement()
            statement.amount = Decimal('0') - total_amount
            statement.description = 'Termination of investment plan'
            statement.type = STATEMENT_TYPE
            statement.account = account
            statement.fk = foreign_key
            statement.save()

            statement = Statement()
            statement.amount = pay_amount
            statement.description = 'Return of invested amount'
            statement.type = STATEMENT_TYPE_RETURN
            statement.account = checking_account
            statement.fk = foreign_key
            statement.save()

            still_has_reinvestments = reinvestments_qs.exists()

            item.amount = reserved
            item.save()

            if not still_has_reinvestments:
                item.status = Investments.STATUS.consumed
                item.save()
            else:
                # Downgrade plan
                plan = Plans.get_by_amount(reserved)

                if plan.pk != item.plan_grace_period.plan.pk:
                    plan_grace_period = PlanGracePeriods.objects.get(plan=plan, grace_period=item.plan_grace_period.grace_period)
                    item.plan_grace_period = plan_grace_period
                    item.save()

                    # Remove all incomes and recalc them
                    start_date = timezone.now() + timedelta(days=1)
                    last_reinvestment = Reinvestments.objects.filter(investment=item).order_by('-created').first()
                    end_date = last_reinvestment.end_date

                    Incomes.objects.filter(investment=item, date__gte=start_date.date(), date__lte=end_date.date()).delete()

                    if last_reinvestment.remaining_months <= 0:
                        continue

                    range_dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
                    income_amount = (item.amount * (plan_grace_period.income_percent / 100)) * last_reinvestment.remaining_months
                    income_table = decimal_split(income_amount, len(range_dates), 98, 100)

                    date_index = 0
                    bulk_incomes = []

                    for dt in range_dates:
                        income = Incomes()
                        income.date = dt
                        income.amount = income_table[date_index]
                        income.investment = item
                        bulk_incomes.append(income)

                        date_index += 1

                    Incomes.objects.bulk_create(bulk_incomes)

            print('Auto withdraw (re)investment of {} from {} user'.format(message_amount, item.account.user.username))


class Command(BaseCommand):
    help = 'Auto withdraw investments and reinvestiments when investment plan grace period ends'

    def handle(self, *args, **options):
        while True:
            withdraw_investments()
