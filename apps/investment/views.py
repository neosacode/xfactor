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
from django.db.models import Q
from jsonview.decorators import json_view

from .models import Plans, Investments, PlanGracePeriods

from exchange_core.models import Accounts, Statement, Users, Currencies
from exchange_core.views import SignupView
from apps.investment.forms import SignupForm, CourseSubscriptionForm
from apps.investment.models import Graduations, Referrals, Incomes, Loans, Credits
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
                investment.account = investment_account
                investment.amount = amount
                investment.status = Investments.STATUS.paid
                investment.paid_date = timezone.now()
                investment.save()


                if grace_period.grace_period.months > 0:
                    start_date = datetime.now() + timedelta(days=1)
                    end_date = start_date + relativedelta(months=grace_period.grace_period.months)
                    range_dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
                    income_amount = (amount * (grace_period.income_percent / 100)) * grace_period.grace_period.months
                    income_table = decimal_split(income_amount, len(range_dates), 98, 100)

                    date_index = 0
                    bulk_incomes = []

                    for dt in range_dates:
                        income = Incomes()
                        income.date = dt
                        income.amount = income_table[date_index]
                        income.investment = investment
                        bulk_incomes.append(income)

                        date_index += 1

                    Incomes.objects.bulk_create(bulk_incomes)

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


@method_decorator(login_required, name='dispatch')
class MyCustomersView(TemplateView):
    template_name = 'investment/my-customers.html'

    def get(self, request):
        user = request.user
        referrals = Referrals.objects.filter(Q(promoter=user) | Q(advisor=user))
        context = self.get_context_data()
        context['referrals'] = referrals
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class CreditLineView(TemplateView):
    template_name = 'investment/credit-line.html'

    def get(self, request):
        loans = Loans.objects.filter(account__user=request.user)
        credits = Credits.objects.filter(account__user=request.user)
        return render(request, self.template_name, {'page_title': _('Credit Line'), 'loans': loans, 'credits': credits})

    def post(self, request):
        form_type = request.POST.get('form_type')

        # Verifica se o formulário enviado é de empréstimo ou de crédito
        if form_type == 'loan':
            # Valor a ser emprestado
            amount = round(Decimal(request.POST.get('amount').replace(',', '.')), 8)
            # Numero de parcelas do empréstimo segundo a tabela
            times = int(request.POST.get('times'))
            # Parcelas
            installments = generate_fixed_loan_table(request.user.active_charge, amount, times=times, raw_date=True)

            # Verifica se o token 2FA digita está correto, valida se a quantidade de parcelas selecionadas bate com a quantidade gerada pelo sistema 
            # e verifica se o usuário tem limite de cŕedito para realizar o empréstimo
            timestamp = time.time()
            seconds = int(timestamp) - int(request.session.get('token_validate_timestamp', 0))

            if seconds <= 5 and times == len(installments['data']) and request.user.loan_available >= amount and amount >= settings.MIN_WITHDRAW:
                # Faz tudo via transação no banco
                with transaction.atomic():
                    # Cria o saldo negativo do empréstimo
                    statement = Statement()
                    statement.charge_in_force = request.user.active_charge
                    statement.description = settings.LOAN_DESCRIPTION
                    statement.type = 'credit'
                    # Gera saldo negativo subtraindo o valor emprestado - zero
                    statement.value = amount
                    statement.save()

                    # Cria um novo empréstimo associando o saldo negativo a ele
                    loan = Loans()
                    loan.statement = statement
                    loan.borrowed_amount = amount
                    loan.total_amount = installments['data'][0]['total_amount']
                    loan.times = times
                    loan.save()

                    last_amount = amount

                    for installment in installments['data']:
                        # Cria as parcelas
                        inst = Installments()
                        inst.loan = loan
                        inst.order = installment['times']
                        inst.due_date = installment['payment_date']
                        inst.interest_percent = installment['interest_percent']
                        inst.amount = Decimal(installment['amount'])
                        inst.save()

                        # Armazena o ultimo saldo para ser usada na proxima parcela
                        last_amount = installment['amount']

                messages.success(request, _("Your loan application was created with success!"))
        else:
            # Valor a ser emprestado
            amount = round(Decimal(request.POST.get('amount').replace(',', '.')), 8)

            # Verifica se o token 2FA digita está correto, valida se a quantidade de parcelas selecionadas bate com a quantidade gerada pelo sistema 
            # e verifica se o usuário tem limite de cŕedito para realizar o empréstimo
            timestamp = time.time().email
            seconds = int(timestamp) - int(request.session.get('token_validate_timestamp', 0))

            if seconds <= 5 and request.user.credit_available >= amount and amount >= settings.MIN_WITHDRAW:
                with transaction.atomic():
                    # Cria o saldo negativo do empréstimo
                    statement = Statement()
                    statement.charge_in_force = request.user.active_charge
                    statement.description = settings.OVERDRAFT_DESCRIPTION
                    # Gera saldo negativo subtraindo o valor emprestado - zero
                    statement.value = amount
                    statement.type = 'credit'
                    statement.save()

                    gateway = Gateway(grace_period.plan.cp_public_key, grace_period.plan.cp_private_key)
                    transaction = gateway.create_transaction(request.user.email, amount)
                    address = transaction['result']['address']

                    # Cria o novo credito
                    credit = Credits()
                    credit.statement = statement
                    credit.borrowed_amount = amount
                    credit.total_amount = amount
                    credit.payment_address = address
                    credit.due_date = timezone.now() + timedelta(days=request.user.active_charge.plan_grace_period.plan.interest_free_days)
                    credit.save()

                messages.success(request, _("Your credit application was created with success!"))

        return redirect(reverse('financial-credit-line'))


@method_decorator(login_required, name='dispatch')
class GenerateLoanTableView(TemplateView):
    def get(self, request):
        charge = Charges.objects.get(pk=request.GET.get('charge'))
        borrow_amount = Decimal(request.GET.get('amount'))
        return JsonResponse(generate_loan_table(charge, borrow_amount))
