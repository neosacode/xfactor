from django.core.management.base import BaseCommand
from django.db import transaction

from apps.investment.models import Comissions, Reinvestments, Referrals, Graduations


class Command(BaseCommand):
    help = 'Pay customer comissions'

    def pay_comission(self, investment, reinvestment, referral, investor, comission_amount):
        comission = Comissions()
        comission.referral = referral
        comission.investment = investment
        comission.reinvestment = reinvestment
        comission.amount = comission_amount
        comission.created = investment.paid_date
        comission.save()

        investment_account = investor.accounts.filter(currency__type='investment').first()
        investment_account.to_deposit(comission_amount)

        print('Paying comission of {} to user {} from {}'.format(comission_amount, investor.username, reinvestment.amount))

    def handle(self, *args, **options):
        while True:
            with transaction.atomic():
                reinvestments = Reinvestments.objects.order_by('-created')

                for item in reinvestments:
                    if Comissions.objects.filter(reinvestment=item).exists():
                        continue

                    user = item.investment.account.user

                    try:
                        referral = Referrals.objects.get(user=user)
                    except:
                        continue

                    plan = item.investment.plan_grace_period.plan
                    promoter = referral.promoter
                    advisor = referral.advisor
                    amount = item.amount

                    # Paga para promoter e para advisor. O promoter pode estar graduado como advisor
                    if promoter and not advisor:
                        promoter_graduation = Graduations.get_present(promoter)

                        if promoter_graduation.type == Graduations._promoter:
                            promoter_comission = (plan.promoter_comission / 100) * amount
                            self.pay_comission(item.investment, item, referral, promoter, promoter_comission)
                        elif promoter_graduation.type == Graduations._advisor:
                            promoter_comission = (plan.advisor_comission / 100) * amount
                            self.pay_comission(item.investment, item, referral, promoter, promoter_comission)
                        else:
                            continue
                    # Paga para promoter e advisor com a diferenca para o advisor
                    elif promoter and advisor and promoter.pk != advisor.pk:
                        difference = abs(plan.advisor_comission - plan.promoter_comission)
                        promoter_comission = (plan.promoter_comission / 100) * amount
                        advisor_comission = (difference / 100) * amount
                        self.pay_comission(item.investment, item, referral, promoter, promoter_comission)
                        self.pay_comission(item.investment, item, referral, advisor, advisor_comission)
                    else:
                        continue

