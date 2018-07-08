from decimal import Decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pytest

from factories import InvestmentFactory, AccountFactory, ReinvestmentFactory, PlanGracePeriodFactory
from apps.investment.management.commands.auto_withdraw_investments import withdraw_investments


@pytest.mark.django_db
def test_auto_withdraw_investment():
    paid_date = datetime.now() - relativedelta(months=12)
    investment = InvestmentFactory(paid_date=paid_date)
    investment_account = investment.account
    checking_account = AccountFactory(user=investment.account.user, currency__type='checking')

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.01000000')
    assert checking_account.deposit == Decimal('0')

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()

    assert investment.status == 'consumed'
    assert investment_account.reserved == Decimal('0')
    assert checking_account.deposit == Decimal('0.009')


@pytest.mark.django_db
def test_auto_withdraw_reinvestment_status():
    paid_date = datetime.now() - relativedelta(months=12)
    reinvestment = ReinvestmentFactory(investment__paid_date=paid_date, investment__amount=Decimal('0.02'),
                                       investment__account__reserved=Decimal('0.02'))
    investment = reinvestment.investment
    investment_account = reinvestment.investment.account
    checking_account = AccountFactory(user=investment.account.user, currency__type='checking')

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.02')
    assert checking_account.deposit == Decimal('0')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'paid'

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()
    reinvestment.refresh_from_db()

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.01')
    assert checking_account.deposit == Decimal('0.009')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'paid'

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()
    reinvestment.refresh_from_db()

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.01')
    assert checking_account.deposit == Decimal('0.009')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'paid'


@pytest.mark.django_db
def test_auto_withdraw_reinvestment():
    paid_date = datetime.now() - relativedelta(months=12)

    reinvestment = ReinvestmentFactory(investment__paid_date=paid_date, investment__amount=Decimal('0.02'),
                                       investment__account__reserved=Decimal('0.02'), created=paid_date)

    investment = reinvestment.investment
    investment_account = reinvestment.investment.account
    checking_account = AccountFactory(user=investment.account.user, currency__type='checking')

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.02')
    assert checking_account.deposit == Decimal('0')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'paid'

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()
    reinvestment.refresh_from_db()

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.01')
    assert checking_account.deposit == Decimal('0.009')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'paid'

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()
    reinvestment.refresh_from_db()

    assert investment.status == 'consumed'
    assert investment_account.reserved == Decimal('0.00')
    assert checking_account.deposit == Decimal('0.018')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'consumed'


@pytest.mark.django_db
def test_auto_withdraw_reinvestments():
    paid_date = datetime.now() - relativedelta(months=12)
    paid_date2 = datetime.now() - relativedelta(months=12)

    reinvestment = ReinvestmentFactory(investment__paid_date=paid_date, investment__amount=Decimal('0.03'),
                                       investment__account__reserved=Decimal('0.03'), created=paid_date)
    reinvestment2 = ReinvestmentFactory(investment=reinvestment.investment, created=paid_date2)

    investment = reinvestment.investment
    investment_account = reinvestment.investment.account
    checking_account = AccountFactory(user=investment.account.user, currency__type='checking')

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.03')
    assert checking_account.deposit == Decimal('0')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'paid'

    assert reinvestment2.amount == Decimal('0.01')
    assert reinvestment2.amount_before == Decimal('0.01')
    assert reinvestment2.membership_fee == Decimal('0')
    assert reinvestment2.status == 'paid'

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()
    reinvestment.refresh_from_db()

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.02')
    assert checking_account.deposit == Decimal('0.009')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'paid'

    assert reinvestment2.amount == Decimal('0.01')
    assert reinvestment2.amount_before == Decimal('0.01')
    assert reinvestment2.membership_fee == Decimal('0')
    assert reinvestment2.status == 'paid'

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()
    reinvestment.refresh_from_db()
    reinvestment2.refresh_from_db()

    assert investment.status == 'paid'
    assert investment_account.reserved == Decimal('0.01')
    assert checking_account.deposit == Decimal('0.018')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'consumed'

    assert reinvestment2.amount == Decimal('0.01')
    assert reinvestment2.amount_before == Decimal('0.01')
    assert reinvestment2.membership_fee == Decimal('0')
    assert reinvestment2.status == 'paid'

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()
    reinvestment.refresh_from_db()
    reinvestment2.refresh_from_db()

    assert investment.status == 'consumed'
    assert investment_account.reserved == Decimal('0')
    assert checking_account.deposit == Decimal('0.027')

    assert reinvestment.amount == Decimal('0.01')
    assert reinvestment.amount_before == Decimal('0.01')
    assert reinvestment.membership_fee == Decimal('0')
    assert reinvestment.status == 'consumed'

    assert reinvestment2.amount == Decimal('0.01')
    assert reinvestment2.amount_before == Decimal('0.01')
    assert reinvestment2.membership_fee == Decimal('0')
    assert reinvestment2.status == 'consumed'


@pytest.mark.django_db
def test_auto_withdraw_income_payment():
    paid_date = datetime.now() - relativedelta(months=12)
    reinvestment = ReinvestmentFactory(investment__paid_date=paid_date, investment__amount=Decimal('0.02'),
                                       investment__account__reserved=Decimal('0.02'), investment__account__deposit=Decimal('0.01'), created=paid_date)
    investment = reinvestment.investment
    investment_account = investment.account
    checking_account = AccountFactory(user=investment.account.user, currency__type='checking')

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()

    assert investment.amount == Decimal('0.01')
    assert investment_account.deposit == Decimal('0')
    assert investment_account.reserved == Decimal('0.01')
    assert checking_account.deposit == Decimal('0.018')

    withdraw_investments()
    investment.refresh_from_db()
    investment_account.refresh_from_db()
    checking_account.refresh_from_db()

    assert investment.amount == Decimal('0')
    assert investment_account.deposit == Decimal('0')
    assert investment_account.reserved == Decimal('0')
    assert checking_account.deposit == Decimal('0.027')


@pytest.mark.django_db
def test_auto_withdraw_downgrade():
    kwargs = {
        'plan__name': 'MUTUAL FUNDS',
        'plan__min_down': Decimal('0.10000000'),
        'plan__max_down': Decimal('0.99999999'),
        'plan__min_reinvest': Decimal('0.03000000'),
        'plan__membership_fee': Decimal('0.01000000'),
        'plan__promoter_comission': Decimal('3.00000000'),
        'plan__advisor_comission': Decimal('6.00000000')
    }

    plan_grace_period = PlanGracePeriodFactory(**kwargs)
    paid_date = datetime.now() - relativedelta(months=12)
    reinvestment = ReinvestmentFactory(investment__paid_date=paid_date, investment__amount=Decimal('1'),
                                       investment__account__reserved=Decimal('1'), amount_before=Decimal('0.91'), amount=Decimal('0.09'))
    investment = reinvestment.investment
    investment.plan_grace_period = plan_grace_period
    investment.save()

    reinvestment.new_invest = plan_grace_period
    reinvestment.save()

    AccountFactory(user=investment.account.user, currency__type='checking')

    assert reinvestment.amount_before == Decimal('0.91')
    assert reinvestment.amount == Decimal('0.09')
    assert investment.amount == Decimal('1')
    assert investment.plan_grace_period.plan.name == 'MUTUAL FUNDS'
    assert reinvestment.old_invest.plan.name == 'SAVINGS'
    assert reinvestment.new_invest.plan.name == 'MUTUAL FUNDS'

    withdraw_investments()
    reinvestment.refresh_from_db()
    investment.refresh_from_db()

    assert investment.amount == Decimal('0.09')
    assert reinvestment.old_invest.plan.name == 'SAVINGS'
    assert reinvestment.new_invest.plan.name == 'MUTUAL FUNDS'

