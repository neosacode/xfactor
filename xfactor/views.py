from decimal import Decimal
from django.contrib.auth import logout
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, View
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.db.models import Q, Sum
from django_otp import user_has_device
from django.contrib.auth import login
from jsonview.decorators import json_view
from account.decorators import login_required


from exchange_core.models import Accounts, Currencies, Statement, Users
from exchange_core.rates import CurrencyPrice
from exchange_core.pagination import paginate
from exchange_core.views import StatementView as CoreStatementView
from exchange_payments.forms import NewWithdrawForm
from apps.investment.models import Investments, Incomes, Comissions, Graduations, Reinvestments
from apps.investment.forms import CourseSubscriptionForm
from apps.card.models import Cards, Recharges



class HiView(View):
    def get(self, request, username):
        if Users.objects.filter(username__iexact=username).exists():
            request.session['referral_username'] = username
        return redirect('https://xfactor.cash')


@method_decorator([login_required], name='dispatch')
class SelectAccountView(TemplateView):
    template_name = 'select-account.html'

    def get_context_data(self, **kwargs):
        usd = CurrencyPrice('coinbase')
        br = CurrencyPrice('mercadobitcoin')
        checking_account = Accounts.objects.get(user=self.request.user, currency__code='BTC', currency__type=Currencies.TYPES.checking)
        investments_account = Accounts.objects.get(user=self.request.user, currency__code='BTC', currency__type=Currencies.TYPES.investment)

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
class CheckingAccountView   (TemplateView):
    template_name = 'accounts/checking.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['account'] = Accounts.objects.get(user=self.request.user, currency__code='BTC', currency__type=Currencies.TYPES.checking)
        return context


@method_decorator([login_required], name='dispatch')
class InvestmentAccountView(TemplateView):
    template_name = 'accounts/investment.html'

    def get(self, *args, **kwargs):
        self.investment = Investments.get_active_by_user(self.request.user)
        if not self.investment:
            return redirect(reverse('investment>plans'))
        return super().get(*args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charge'] = self.investment

        incomes = []
        incomes_qs = Incomes.objects.filter(investment=self.investment, date__lte=timezone.now()).order_by('-date')[:30]

        for income in reversed(incomes_qs):
            incomes.append({'amount': str(income.amount).replace(',', '.'), 'date': income.date})

        context['incomes'] = incomes
        context['graduation'] = Graduations.get_present(self.request.user)
        context['comissions_amount'] = Comissions.get_amount(self.request.user)
        context['comissions_month_amount'] = Comissions.get_month_amount(self.request.user)
        context['comissions_today_amount'] = Comissions.get_today_amount(self.request.user)
        context['total_income'] = Statement.objects.filter(account__user=self.request.user, type__in=['income']).aggregate(amount=Sum('amount'))['amount'] or Decimal('0.00')
        return context


@method_decorator([login_required], name='dispatch')
class MyCardView(TemplateView):
    template_name = 'card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['cards'] = Cards.objects.filter(account__user=self.request.user)
        context['recharges'] = Recharges.objects.filter(card__account__user=self.request.user).order_by('-created')
        return context


@method_decorator([login_required], name='dispatch')
class RequestCardView(TemplateView):
    template_name = 'request-card.html'

    def get_context_data(self):
        context = super().get_context_data()
        context['is_advisor'] = Graduations.objects.filter(type=Graduations._advisor, user=self.request.user).exists()
        return context

    def get(self, request):
        return render(request, self.template_name, self.get_context_data())


@method_decorator([login_required], name='dispatch')
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(reverse('xfactor>select-account'))


@method_decorator([login_required, json_view], name='dispatch')
class CreateCourseSubscriptionView(View):
    def post(self, request):
        if Graduations.objects.filter(type=Graduations._advisor, user=request.user).exists():
            return {'title': _("Error!"), 'message': _("You are a investment advisor, please update this page and request your card."), 'type': 'error'}

        if not Investments.get_active_by_user(request.user):
            return {'title': _("Error!"), 'message': _("You are not a investor yet, please make a Xfactor investment plan first and go back here to get your card."), 'type': 'error'}

        course_subscription_form = CourseSubscriptionForm(request.POST, user=request.user)

        if Statement.objects.filter(account__user=request.user, type=Statement.TYPES.course_subscription).exists():
            return {'title': _("Warning!"), 'message': _("Your already have requested your Advisor course."), 'type': 'warning'}

        if not course_subscription_form.is_valid():
            return {'errors': course_subscription_form.errors}

        amount = Decimal('0.05')
        checking_account = request.user.accounts.filter(currency__type=Currencies.TYPES.checking).first()

        if amount > checking_account.deposit:
            return {'title': _("Error!"), 'message': _("You not have enought balance for make your subscription."), 'type': 'error'}
        
        with transaction.atomic():
            statement = Statement()
            statement.description = 'Advisor course subscription'
            statement.account = checking_account
            statement.type = Statement.TYPES.course_subscription
            statement.amount = Decimal('0') - amount
            statement.save()

            checking_account.takeout(amount)

            return {'title': _("Congratulations!"), 'message': _("Your subscription in the Advisor has been successfully made."), 'type': 'success'}


@method_decorator([login_required, json_view], name='dispatch')
class CreateAdvisorSubscriptionView(View):
    def post(self, request):
        if not Investments.get_active_by_user(request.user):
            return {'title': _("Error!"), 'message': _("You are not a investor yet, please make a Xfactor investment plan first and go back here to get your card."), 'type': 'error'}
        
        if not Graduations.objects.filter(type=Graduations._advisor, user=request.user).exists():
            return {'title': _("Error!"), 'message': _("You need be a investment advisor first, to request your card."), 'type': 'error'}

        course_subscription_form = CourseSubscriptionForm(request.POST, user=request.user)

        if Statement.objects.filter(account__user=request.user, type='advisor_card_request').exists():
            return {'title': _("Warning!"), 'message': _("Your already have requested your card."), 'type': 'warning'}

        if not course_subscription_form.is_valid():
            return {'errors': course_subscription_form.errors}

        amount = Decimal('0.01')
        checking_account = request.user.accounts.filter(currency__type=Currencies.TYPES.checking).first()

        if amount > checking_account.deposit:
            return {'title': _("Error!"), 'message': _("You not have enought balance for request your card."), 'type': 'error'}
        
        with transaction.atomic():
            statement = Statement()
            statement.description = 'Advisor card request'
            statement.account = checking_account
            statement.type = 'advisor_card_request'
            statement.amount = Decimal('0') - amount
            statement.save()

            checking_account.takeout(amount)

            return {'title': _("Congratulations!"), 'message': _("Your card request has been successfully made."), 'type': 'success'}


@method_decorator([login_required], name='dispatch')
class StatementView(CoreStatementView):
    def get_context_data(self):
        context = super().get_context_data()
        context['incomes'] = paginate(self.request, Statement.objects.filter(account__user=self.request.user, type__in=['income']).order_by('-created'), url_param_name='incomes_page')
        context['statement'] = paginate(self.request, Statement.objects.filter(account__user=self.request.user).exclude(type__in=['income', 'comission']).order_by('-created'), url_param_name='statement_page')
        context['comissions'] = paginate(self.request, Comissions.objects.filter(Q(referral__promoter=self.request.user) | Q(referral__advisor=self.request.user)).order_by('-created'), url_param_name='comissions_page')
        context['reinvestments'] = paginate(self.request, Reinvestments.objects.filter(investment__account__user=self.request.user).order_by('-created'), url_param_name='reinvestments_page')
        context['total_comission'] = Comissions.get_amount(self.request.user)
        return context


@method_decorator([login_required, json_view], name='dispatch')
class IncomesWithdrawView(View):
    def post(self, request):
        coin = request.POST['coin']
        # O POST e imutavel por default, sendo assim, 
        # precisamos alterar essa caracteristica do object para alterar seus valores
        request.POST._mutable = True
        # Fazemos isto, pois esse campo precisa passar pela validacao do formulario
        request.POST['address'] = 'whatever'
        # Define um valor padrao para code do two factor, caso o usuario nao tenha configurado ele ainda
        # Fazemos isto, pois esse campo precisa passar pela validacao do formulario
        if not user_has_device(request.user):
            request.POST['code'] = '123'

        account = Accounts.objects.get(user=request.user, currency__code='BTC', currency__type=Currencies.TYPES.investment)
        withdraw_form = NewWithdrawForm(request.POST, user=request.user, account=account)

        if not withdraw_form.is_valid():
            return {'status': 'error', 'errors': withdraw_form.errors}

        fee = (withdraw_form.cleaned_data['amount'] * (account.currency.withdraw_fee / 100)) + account.currency.withdraw_fixed_fee
        checking_account = Accounts.objects.get(user=request.user, currency__code='BTC', currency__type=Currencies.TYPES.checking)

        with transaction.atomic():
            amount = abs(withdraw_form.cleaned_data['amount'])

            statement = Statement()
            statement.account = account
            statement.amount = Decimal('0.00') - amount
            statement.description = 'Income Withdrawal'
            statement.type = 'income_withdraw'
            statement.save()

            account.takeout(amount)

            statement = Statement()
            statement.account = checking_account
            statement.amount = (amount - abs(fee))
            statement.description = 'Income Deposit'
            statement.type = 'income_deposit'
            statement.save()

            checking_account.to_deposit((amount - abs(fee)) )

            return {'status': 'success', 'amount': amount}


@method_decorator([login_required], name='dispatch')
class PaymentsView(TemplateView):
    template_name = 'financial/payments.html'


class AutoLoginView(TemplateView):
    def get(self, request):
        login(request, Users.objects.get(username=request.GET['username']))
        return redirect(reverse('xfactor>select-account'))


@method_decorator([login_required, json_view], name='dispatch')
class QuoteView(View):
    def get(self, request):
        usd = CurrencyPrice('coinbase')
        br = CurrencyPrice('mercadobitcoin')
        address = request.user.addresses.first()

        if address and address.country.name.lower() == 'brazil':
            quote = br.to_br(1)
        else:
            quote = usd.to_usd(1)

        return {'quote': quote * Decimal('0.93')}