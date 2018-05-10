import uuid

from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from account.decorators import login_required


from exchange_core.models import Accounts, Currencies
from exchange_core.rates import CurrencyPrice
from apps.investment.models import Charges


@method_decorator([login_required], name='dispatch')
class SelectAccountView(TemplateView):
	template_name = 'select-account.html'

	def get_context_data(self, **kwargs):
		usd = CurrencyPrice('coinbase')
		br = CurrencyPrice('mercadobitcoin')
		checking_account = Accounts.objects.get(user=self.request.user, currency__symbol='BTC', currency__type=Currencies.TYPES.checking)
		investments_account = Accounts.objects.get(user=self.request.user, currency__symbol='BTC', currency__type=Currencies.TYPES.investment)

		context = super().get_context_data(**kwargs)
		context['btc_usd_price'] = usd.to_usd(1)
		context['btc_br_price'] = br.to_br(1)
		context['checking_account'] = checking_account
		context['investments_account'] = investments_account
		context['checking_account_usd_price'] = usd.to_usd(checking_account.balance)
		context['investments_account_usd_price'] = usd.to_usd(investments_account.balance)
		context['checking_account_br_price'] = br.to_br(checking_account.balance)
		context['investments_account_br_price'] = br.to_br(investments_account.balance)
		return context


@method_decorator([login_required], name='dispatch')
class CheckingAccountView	(TemplateView):
	template_name = 'accounts/checking.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['account'] = Accounts.objects.get(user=self.request.user, currency__symbol='BTC', currency__type=Currencies.TYPES.checking)
		return context


@method_decorator([login_required], name='dispatch')
class InvestmentAccountView(TemplateView):
	template_name = 'accounts/investment.html'

	def get(self, *args, **kwargs):
		try:
			charge = Charges.objects.get(account__user=self.request.user)
		except Charges.DoesNotExist:
			return redirect(reverse('investment>plans'))
		return super().get(*args, **kwargs)


	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['charge'] = Charges.objects.get(account__user=self.request.user)
		return context


@method_decorator([login_required], name='dispatch')
class MyCardView(TemplateView):
	template_name = 'card.html'


@method_decorator([login_required], name='dispatch')
class RequestCardView(TemplateView):
	template_name = 'request-card.html'