from decimal import Decimal
from datetime import datetime

import factory

from exchange_core.models import Users, Currencies, Accounts
from apps.investment.models import Investments, Plans, GracePeriods, PlanGracePeriods, Reinvestments


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = Users

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.Faker('user_name')
    email = factory.Faker('email')
    password = factory.PostGenerationMethodCall('set_password', '123456')


class CurrencyFactory(factory.DjangoModelFactory):
    class Meta:
        model = Currencies
        django_get_or_create = ('symbol', 'type',)

    name = 'Bitcoin'
    symbol = 'BTC'
    type = Currencies.TYPES.investment
    withdraw_fee = Decimal('10.00')


class AccountFactory(factory.DjangoModelFactory):
    class Meta:
        model = Accounts

    user = factory.SubFactory(UserFactory)
    currency = factory.SubFactory(CurrencyFactory)
    reserved = Decimal('0.01000000')


class PlanFactory(factory.DjangoModelFactory):
    class Meta:
        model = Plans
        django_get_or_create = ('name',)

    name = 'SAVINGS'
    min_down = Decimal('0.01000000')
    max_down = Decimal('0.09999999')
    min_reinvest = Decimal('0.01000000')
    membership_fee = Decimal('0.00350000')
    promoter_comission = Decimal('2.00000000')
    advisor_comission = Decimal('5.00000000')


class GracePeriodFactory(factory.DjangoModelFactory):
    class Meta:
        model = GracePeriods
        django_get_or_create = ('months',)

    months = 12


class PlanGracePeriodFactory(factory.DjangoModelFactory):
    class Meta:
        model = PlanGracePeriods
        django_get_or_create = ('plan', 'grace_period',)

    plan = factory.SubFactory(PlanFactory)
    grace_period = factory.SubFactory(GracePeriodFactory)
    income_percent = Decimal('4.00000000')
    payment_type = PlanGracePeriods.TYPES.monthly
    currency = factory.SubFactory(CurrencyFactory)


class InvestmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Investments

    plan_grace_period = factory.SubFactory(PlanGracePeriodFactory)
    amount = Decimal('0.01000000')
    membership_fee = Decimal('0.00350000')
    account = factory.SubFactory(AccountFactory)
    paid_date = factory.LazyFunction(datetime.now)


class ReinvestmentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Reinvestments

    old_invest = factory.SubFactory(PlanGracePeriodFactory)
    new_invest = factory.SubFactory(PlanGracePeriodFactory)
    amount = Decimal('0.01')
    amount_before = Decimal('0.01')
    incomes = Decimal('0')
    membership_fee = Decimal('0')
    investment = factory.SubFactory(InvestmentFactory)
    status = Reinvestments.STATUS.paid
    created = factory.LazyFunction(datetime.now)