import uuid

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import logout
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, View
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.db import transaction
from jsonview.decorators import json_view
from account.decorators import login_required


from exchange_core.models import Accounts, Currencies, Statement
from exchange_core.rates import CurrencyPrice
from apps.investment.models import Investments, Incomes
from apps.investment.forms import CourseSubscriptionForm


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
			self.investment = Investments.objects.get(account__user=self.request.user)
		except Investments.DoesNotExist:
			return redirect(reverse('investment>plans'))
		return super().get(*args, **kwargs)


	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['charge'] = self.investment

		incomes = []
		incomes_qs = Incomes.objects.filter(investment=self.investment, date__lte=timezone.now()).order_by('-date')[:30]
		increment_amount = 0

		for income in reversed(incomes_qs):
			incomes.append({'amount': str(income.amount).replace(',', '.'), 'date': income.date})

		context['incomes'] = incomes
		return context


@method_decorator([login_required], name='dispatch')
class MyCardView(TemplateView):
	template_name = 'card.html'


@method_decorator([login_required], name='dispatch')
class RequestCardView(TemplateView):
	template_name = 'request-card.html'


@method_decorator([login_required], name='dispatch')
class LogoutView(View):
	def get(self, request):
		logout(request)
		return redirect(reverse('xfactor>select-account'))


@method_decorator([login_required, json_view], name='dispatch')
class CreateCourseSubscriptionView(View):
    def post(self, request):
        course_subscription_form = CourseSubscriptionForm(request.POST, user=request.user)        

        if Statement.objects.filter(account__user=request.user, type=Statement.TYPES.course_subscription).exists():
        	return {'title': _("Warning!"), 'message': _("Your already have requested your Advisor course."), 'type': 'warning'}

        if not course_subscription_form.is_valid():
            return {'errors': course_subscription_form.errors}

        amount = Decimal('0.03')
        checking_account = request.user.accounts.filter(currency__type=Currencies.TYPES.checking).first()

        if amount > checking_account.deposit:
        	return {'title': _("Error!"), 'message': _("You not have enought balance for make your subscription ."), 'type': 'error'}
        
        with transaction.atomic():
        	statement = Statement()
        	statement.description = 'Advisor course subscription'
        	statement.account = checking_account
        	statement.type = Statement.TYPES.course_subscription
        	statement.amount = Decimal('0') - amount
        	statement.save()

        	checking_account.takeout(amount)

        	return {'title': _("Congratulations!"), 'message': _("Your subscription in the Advisor has been successfully made."), 'type': 'success'}
