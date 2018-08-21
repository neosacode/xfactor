from django.core.management.base import BaseCommand
from apps.card.models import Recharges



class Command(BaseCommand):
    help = 'Auto withdraw investments and reinvestiments when investment plan grace period ends'

    def handle(self, *args, **options):
        print('cpf', 'valor', sep=',')
        for recharge in Recharges.objects.all():
            print(recharge.card.account.user.document_1, recharge.quote_amount, sep=',')
