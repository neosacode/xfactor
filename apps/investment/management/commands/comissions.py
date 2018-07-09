from django.core.management.base import BaseCommand
from django.db import transaction

from apps.investment.models import Comissions, Investments, Referrals, Graduations


def pay_comission(investment, referral, investor, comission_amount):
    comission = Comissions()
    comission.referral = referral
    comission.investment = investment
    comission.amount = comission_amount
    comission.created = investment.paid_date
    comission.save()

    investment_account = investor.accounts.filter(currency__type='investment').first()
    investment_account.to_deposit(comission_amount)

    print('Paying comission of {} to user {}'.format(comission_amount, investor.username))


def pay_investments_comissions():
    with transaction.atomic():
        investments = Investments.objects.filter(status=Investments.STATUS.paid).order_by('-created')

        for item in investments:
            if Comissions.objects.filter(investment=item).exists():
                continue

            user = item.account.user

            try:
                referral = Referrals.objects.get(user=user)
            except:
                continue

            promoter_investment = Investments.get_active_by_user(referral.promoter)
            advisor_investment = Investments.get_active_by_user(referral.advisor)
            promoter_plan = promoter_investment.plan_grace_period.plan if promoter_investment else None
            advisor_plan = promoter_investment.plan_grace_period.plan if advisor_investment else None
            promoter = referral.promoter
            advisor = referral.advisor
            amount = item.amount

            # Paga para promoter e para advisor. O promoter pode estar graduado como advisor
            if promoter and not advisor:
                promoter_graduation = Graduations.get_present(promoter)

                if promoter_graduation.type == Graduations._promoter:
                    promoter_comission = (promoter_plan.promoter_comission / 100) * amount
                    pay_comission(item, referral, promoter, promoter_comission)
                elif promoter_graduation.type == Graduations._advisor:
                    promoter_comission = (promoter_plan.advisor_comission / 100) * amount
                    pay_comission(item, referral, promoter, promoter_comission)
                else:
                    continue
            # Paga para promoter e advisor com a diferenca para o advisor
            elif promoter and advisor and promoter.pk != advisor.pk:
                difference = abs(advisor_plan.advisor_comission - promoter_plan.promoter_comission)
                promoter_comission = (promoter_plan.promoter_comission / 100) * amount
                advisor_comission = (difference / 100) * amount
                pay_comission(item, referral, promoter, promoter_comission)
                pay_comission(item, referral, advisor, advisor_comission)
            else:
                continue

class Command(BaseCommand):
    help = 'Pay customer comissions'

    def handle(self, *args, **options):
        while True:
            pay_investments_comissions()
