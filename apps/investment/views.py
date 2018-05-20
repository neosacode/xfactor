from decimal import Decimal

from datetime import date, datetime
from dateutil.rrule import rrule, DAILY
from dateutil.relativedelta import relativedelta

from django.views.generic import TemplateView, View
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from jsonview.decorators import json_view

from .models import Plans, Investments, PlanGracePeriods

from exchange_core.models import Accounts, Statement, Users, Currencies
from exchange_core.views import SignupView
from apps.investment.forms import SignupForm
from apps.investment.models import Graduations, Referrals, Incomes
from apps.investment.utils import decimal_split


@method_decorator(login_required, name='dispatch')
class PlansView(TemplateView):
    template_name = 'investment/plans.html'

    def get(self, request):
        if Investments.objects.filter(account__user=self.request.user).exists():
            return redirect(reverse('xfactor>investment'))

        plans = Plans.objects.filter(status=Plans.STATUS.active).order_by('order')
        investments = Investments.objects.filter(account__user=request.user)
        return render(request, self.template_name, {'plans': plans, 'investments': investments})


@method_decorator([json_view, login_required], name='dispatch')
class GetPlanLacksView(View):
    def post(self, request):
        periods = PlanGracePeriods.objects.filter(plan__id=request.POST['id'], 
                                               plan__status=Plans.STATUS.active, 
                                               status=PlanGracePeriods.STATUS.active)
        response = []
        for period in periods:
            response.append({'period': period.grace_period.months, 'percent': round(period.income_percent, 0), 'id': period.pk})
        return response


@method_decorator(login_required, name='dispatch')
class MyPlansView(TemplateView):
    template_name = 'financial/my-plans.html'

    def get(self, request):
        user = request.user
        investments = Investments.objects.filter(account__user=user).exclude(status=Investments.STATUS.cancelled)
        return render(request, self.template_name, { 'investments': investments})


@method_decorator([login_required], name='dispatch')
class CancelNoFidelityPlanView(TemplateView):
    def get(self, request):
        investment_id = request.GET['charge']
        investment = Investments.objects.get(account__user=request.user, pk=investment_id)

        if investment.plan_grace_period.grace_period.months > 0:
            messages.error(request, _("This plan can't be cancelled"))

        with transaction.atomic():
            account = investment.account
            account.reserved -= investment.amount
            account.deposit += investment.amount
            account.save()

            investment.status = Investments.STATUS.cancelled
            investment.save()
            
            messages.success(request, _("Your non-fidelity investment has been cancelled"))
        return redirect(reverse('financial-my-plans'))


@method_decorator([login_required, json_view], name='dispatch')
class CreateInvestmentView(View):
    def post(self, request):
        if Investments.objects.filter(account__user=self.request.user).exists():
            return redirect(reverse('xfactor>investment'))

        grace_period_pk = request.POST['grace_period']
        grace_period = PlanGracePeriods.objects.get(pk=grace_period_pk)
        checking_account = Accounts.objects.get(user=request.user, currency__symbol=grace_period.currency.symbol, currency__type=Currencies.TYPES.checking)
        investment_account = Accounts.objects.get(user=request.user, currency=grace_period.currency)

        amount = request.POST.get('amount', '0.00').replace(',', '.')
        amount = ''.join(c for c in amount if c.isdigit() or c == '.')

        if not amount:
            amount = '0.00'

        amount = Decimal(amount)

        if grace_period.plan.min_down > amount or grace_period.plan.max_down < amount:
            return {'message': _("ERROR! The investment amount it is out of the plan limit")}
        elif amount > checking_account.deposit:
            return {'message': _(
                "ERROR! Your {} account does not have enought deposit amount".format(checking_account.currency.name))}
        else:
            with transaction.atomic():
                investment = Investments()
                investment.plan_grace_period = grace_period
                investment.account = checking_account
                investment.amount = amount
                investment.status = Investments.STATUS.paid
                investment.paid_date = timezone.now()
                investment.save()


                if grace_period.grace_period.months > 0:
                    start_date = datetime.now()
                    end_date = start_date + relativedelta(months=grace_period.grace_period.months)
                    range_dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
                    income_amount = (amount * (grace_period.income_percent / 100)) * grace_period.grace_period.months
                    income_table = decimal_split(income_amount, len(range_dates), 98, 100)

                    date_index = 0

                    for dt in range_dates:
                        income = Incomes()
                        income.date = dt
                        income.amount = income_table[date_index]
                        income.investment = investment
                        income.save() 

                        date_index += 1

                checking_account.deposit -= amount
                checking_account.save()

                investment_account.reserved += amount
                investment_account.save()

                statement = Statement()
                statement.account = checking_account
                statement.amount = Decimal('0.00') - amount
                statement.type = Statement.TYPES.investment
                statement.description = 'New investment'
                statement.fk = investment.pk
                statement.save()

                statement = Statement()
                statement.account = investment_account
                statement.amount = amount
                statement.type = Statement.TYPES.investment
                statement.description = 'New investment'
                statement.fk = investment.pk
                statement.save()


            return {'message': _("Congratulations! Your investing plan was created."), 'redirect': True}
        return {'message': _("Someting in your new investment plan didn't work as expected.")}


class ReferrerSignupView(SignupView):
    form_class = SignupForm
    template_name = 'investment/signup.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._use_address = False

    def dispatch(self, *args, **kwargs):
        self.promoter = Users.objects.get(username=self.request.GET['promoter'], graduations__type=Graduations._promoter)
        return super().dispatch(*args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['promoter'] = self.promoter
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['promoter'] = self.promoter
        return context

    def form_valid(self, *args, **kwargs):
        with transaction.atomic():
            return super().form_valid(*args, **kwargs)

    # Sobreescreve o metodo after_signup para popular campos adicionais do usuário
    def after_signup(self, form):
        user = self.created_user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.save()

        referral = Referrals()
        referral.user = user
        referral.promoter = self.promoter
        referral.advisor = form.cleaned_data['advisor']
        referral.save()