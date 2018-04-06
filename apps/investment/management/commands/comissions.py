from django.core.management.base import BaseCommand
from django.db import transaction

from apps.investment.models import Charges, Statement


class Command(BaseCommand):
    help = 'Pay customer comissions'

    def handle(self, *args, **options):
        with transaction.atomic():
            charges = Charges.objects.filter(status='paid')

            for charge in charges:
                sponsor = charge.user.sponsor

                if not sponsor:
                    continue

                description = 'Indication comission from {}'.format(charge.user.username)
                # Verifica se o rendimento já foi para o cliente, se sim pula para o próximo pagamento
                statements = Statement.objects.filter(description=description, charge_in_force=charge.user.sponsor.active_charge)

                if statements.exists():
                    continue

                # Paga por enquanto comissões somente para usuários
                # TODO: Mudar depois para pagar as comissões dos corretores
                comission_amount = round((charge.plan_grace_period.plan.comission_percent / 100) * charge.amount, 8)

                # Cria o rendimento no extrato do cliente
                if not sponsor.active_charge:
                    continue

                statement = Statement()
                statement.charge_in_force = sponsor.active_charge
                statement.value = comission_amount
                statement.description = description
                statement.type = 'comission'
                statement.save()

                print('Pagando {} para o cliente {}'.format(comission_amount, sponsor.username))

