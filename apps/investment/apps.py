from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class Config(AppConfig):
	name = 'apps.investment'
	verbose_name = _('Investments')