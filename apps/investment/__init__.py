from decimal import Decimal

from django.conf import settings
from prettyconf import config


# Tells to Django where it is the configuration class of this module
default_app_config = 'apps.investment.apps.Config'

# Credit line config
settings.LOAN_INTEREST_PERCENT = config('LOAN_INTEREST_PERCENT', cast=Decimal, default=Decimal('30'))
settings.OVERDRAFT_INTEREST_PERCENT = config('LOAN_INTEREST_PERCENT', cast=Decimal, default=Decimal('10'))