import uuid

from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from account.decorators import login_required


from exchange_core.models import Accounts
from exchange_core.rates import CurrencyPrice


@method_decorator([login_required], name='dispatch')
class SelectAccountView(TemplateView):
	template_name = 'select-account.html'

	def get_context_data(self, **kwargs):
		usd_price = CurrencyPrice('coinbase')
		br_price = CurrencyPrice('mercadobitcoin')
		checking_account = Accounts.objects.get(user=self.request.user, currency__symbol='BTC')
		investments_account = Accounts.objects.get(user=self.request.user, currency__symbol='BTCI')

		context = super().get_context_data(**kwargs)
		context['checking_account'] = checking_account
		context['investments_account'] = investments_account
		context['checking_account_usd_price'] = usd_price.to_usd(checking_account.balance)
		context['investments_account_usd_price'] = usd_price.to_usd(investments_account.balance)
		context['checking_account_br_price'] = br_price.to_br(checking_account.balance)
		context['investments_account_br_price'] = br_price.to_br(investments_account.balance)
		return context