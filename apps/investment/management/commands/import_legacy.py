import csv
import dateutil.parser

from django.db import transaction
from django.core.management.base import BaseCommand

from apps.investment.models import Investments

class Command(BaseCommand):
    help = 'Import Legacy Data'

    def handle(self, *args, **options):
        with transaction.atomic():
            with open('apps/investment/management/commands/data/paid.csv', 'r') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    investment = Investments.objects.get(account__user__username=row['username'])
                    paid_date = dateutil.parser.parse(row['paid_date'])

                    investment.paid_date = paid_date
                    investment.save()

                    print(row['username'])