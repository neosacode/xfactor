from decimal import Decimal

import pytest

from exchange_core.models import Statement
from apps.investment.models import Referrals, Comissions
from apps.investment.utils import change_referral
from apps.investment.management.commands.comissions import pay_investments_comissions
from apps.investment.management.commands.pay_course_comission import pay_course_comissions

from factories import UserFactory, ReferralFactory, CurrencyFactory, InvestmentFactory, StatementFactory, GraduationFactory


@pytest.fixture
def currencies():
    investment = CurrencyFactory()
    checking = CurrencyFactory(type='checking')
    return {'investment': investment, 'checking': checking}


@pytest.mark.django_db
def test_referral_not_found_exception():
    with pytest.raises(Referrals.DoesNotExist):
        user = UserFactory()
        promoter = UserFactory()
        change_referral(user, promoter)

@pytest.mark.django_db
def test_referral_was_found():
    user = UserFactory()
    promoter = UserFactory()
    referral = ReferralFactory(user=user, promoter=promoter)

    assert referral.user.pk == user.pk
    assert referral.user.pk == user.pk
    assert referral.promoter.pk == promoter.pk


@pytest.mark.django_db
def test_if_comissions_are_being_properly_returned(currencies):
    user = UserFactory()
    promoter = UserFactory()
    referral = ReferralFactory(user=user, promoter=promoter)
    user_investment = InvestmentFactory(account__user=user)
    promoter_investment = InvestmentFactory(account__user=promoter)
    account = promoter.accounts.filter(currency__type='investment').first()

    assert user_investment.amount == Decimal('0.01')
    assert promoter_investment.amount == Decimal('0.01')

    pay_investments_comissions()
    account.refresh_from_db()

    assert Comissions.objects.count() == 1
    comission = Comissions.objects.first()
    assert comission.amount == Decimal('0.0002')
    assert account.deposit == Decimal('0.0002')
    assert comission.referral.pk == referral.pk

    change_referral(user, promoter)
    account.refresh_from_db()

    assert Comissions.objects.count() == 0
    assert account.deposit == Decimal('0')


@pytest.mark.django_db
def test_if_course_comission_has_being_properly_returned(currencies):
    user = UserFactory()
    promoter = UserFactory()
    new_promoter = UserFactory()
    referral = ReferralFactory(user=user, promoter=promoter)
    user_investment = InvestmentFactory(account__user=user)
    promoter_investment = InvestmentFactory(account__user=promoter)
    checking_account = user.accounts.filter(currency__type='checking').first()
    promoter_investment_account = promoter.accounts.filter(currency__type='investment').first()
    promoter_graduation = GraduationFactory(user=promoter)

    statement = StatementFactory(amount=Decimal('0.03'), type='course_subscription', description='Course Subscription', account=checking_account)
    assert statement.amount == Decimal('0.03')
    assert promoter_graduation.type == 'advisor'

    pay_course_comissions()
    promoter_investment_account.refresh_from_db()

    assert Statement.objects.count() == 1
    assert Comissions.objects.count() == 1
    assert Comissions.objects.first().amount == Decimal('0.003')
    assert promoter_investment_account.deposit == Decimal('0.003')

    change_referral(user, new_promoter)
    promoter_investment_account.refresh_from_db()
    referral.refresh_from_db()

    assert Statement.objects.count() == 0
    assert Comissions.objects.count() == 0
    assert promoter_investment_account.deposit == Decimal('0')
    assert new_promoter.pk == referral.promoter.pk


