from decimal import Decimal

from datetime import date, datetime, timedelta
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
from django.db.models import Q, Sum
from jsonview.decorators import json_view

from .models import Plans, Investments, PlanGracePeriods

from exchange_core.models import Accounts, Statement, Users, Currencies
from exchange_core.views import SignupView
from apps.investment.forms import SignupForm
from apps.investment.models import Graduations, Referrals, Incomes, Loans, Credits, Reinvestments
from apps.investment.utils import decimal_split


@method_decorator(login_required, name='dispatch')
class PlansView(TemplateView):
    template_name = 'investment/plans.html'

    def get(self, request):
        if Investments.get_active_by_user(self.request.user):
            return redirect(reverse('xfactor>investment'))

        plans = Plans.objects.filter(status=Plans.STATUS.active).order_by('order')
        return render(request, self.template_name, {'plans': plans})


@method_decorator([json_view, login_required], name='dispatch')
class GetPlanLacksView(View):
    def post(self, request):
        investment = Investments.get_by_user(request.user)
        periods = PlanGracePeriods.objects.filter(plan__id=request.POST['id'], 
                                               plan__status=Plans.STATUS.active, 
                                               status=PlanGracePeriods.STATUS.active)
        response = []
        for period in periods:
            if investment and investment.plan_grace_period.grace_period.months >= period.grace_period.months:
                continue
            response.append({'period': period.grace_period.months, 'percent': round(period.income_percent, 0), 'id': period.pk})
        return response


@method_decorator([login_required, json_view], name='dispatch')
class CreateInvestmentView(View):
    def post(self, request):
        if Investments.get_active_by_user(self.request.user):
            return {'message': _("ERROR! You already have a investment")}

        grace_period_pk = request.POST['grace_period']
        grace_period = PlanGracePeriods.objects.get(pk=grace_period_pk)
        checking_account = Accounts.objects.get(user=request.user, currency__symbol=grace_period.currency.symbol, currency__type=Currencies.TYPES.checking)
        investment_account = Accounts.objects.get(user=request.user, currency=grace_period.currency)

        amount = request.POST.get('amount', '0.00').replace(',', '.')
        amount = ''.join(c for c in amount if c.isdigit() or c == '.')

        if not amount:
            amount = '0.00'

        amount = Decimal(amount)
        amount_with_fee = amount + grace_period.plan.membership_fee
        min_invest = grace_period.plan.min_down
        max_invest = grace_period.plan.max_down

        if min_invest > amount or max_invest < amount:
            return {'message': _("ERROR! The investment amount it is out of the plan limit")}
        elif amount_with_fee > checking_account.deposit:
            return {'message': _(
                "ERROR! Your {} account does not have enought deposit amount".format(checking_account.currency.name))}
        else:
            with transaction.atomic():
                investment = Investments()
                investment.plan_grace_period = grace_period
                investment.account = investment_account
                investment.amount = amount
                investment.status = Investments.STATUS.paid
                investment.membership_fee = grace_period.plan.membership_fee
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

                checking_account.deposit -= amount_with_fee
                checking_account.save()

                investment_account.reserved += amount
                investment_account.save()

                statement = Statement()
                statement.account = checking_account
                statement.amount = Decimal('0.00') - amount_with_fee
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


@method_decorator(login_required, name='dispatch')
class ReinvestmentView(TemplateView):
    template_name = 'investment/reinvestment.html'

    def get_context_data(self):
        context = super().get_context_data()
        context['plans'] = Plans.objects.filter(status=Plans.STATUS.active).order_by('order')
        context['investment'] = Investments.get_by_user(self.request.user)
        return context


@method_decorator([login_required, json_view], name='dispatch')
class CreateReinvestmentView(View):
    def post(self, request):
        investment = Investments.get_by_user(request.user)
        reinvestment_old_invest = investment.plan_grace_period
        reinvestment_amount_before = investment.account.reserved
        reinvestment_incomes = investment.account.deposit

        grace_period_pk = request.POST['grace_period']
        grace_period = PlanGracePeriods.objects.get(pk=grace_period_pk)
        use_checking = request.POST['use_checking'] in ['true', '1']

        if grace_period.grace_period.months < investment.plan_grace_period.grace_period.months:
            return {'message': _("ERROR! Selected grace period is not valid.")}

        checking_account = Accounts.objects.get(user=request.user, currency__symbol=grace_period.currency.symbol, currency__type=Currencies.TYPES.checking)
        investment_account = Accounts.objects.get(user=request.user, currency=grace_period.currency)

        amount = request.POST.get('amount', '0.00').replace(',', '.')
        amount = ''.join(c for c in amount if c.isdigit() or c == '.')

        if not amount:
            amount = '0.00'

        amount = Decimal(amount)
        reinvestment_amount = amount
        membership_fee = Decimal('0.00')
        amount_with_fee = amount + membership_fee
        amount_with_investment = amount + investment.amount
        reinvest_plan = Plans.objects.filter(min_down__lte=amount_with_investment, max_down__gte=amount_with_investment).order_by('-max_down').first()
        min_reinvest = grace_period.plan.min_reinvest
        months = grace_period.grace_period.months
        grace_period = PlanGracePeriods.objects.get(plan=reinvest_plan, grace_period__months=months)
        reinvestment_new_invest = grace_period

        # Se for um upgrade, soma a diferenca do membership_fee
        if reinvest_plan and reinvest_plan.pk != investment.plan_grace_period.plan.pk:
            membership_fee = (reinvest_plan.membership_fee - investment.plan_grace_period.plan.membership_fee)
            amount_with_fee = amount + membership_fee

        reinvestment_membership_fee = membership_fee
        # Saldo para validacao do reinvestimento
        balance = investment_account.deposit

        if use_checking:
            balance += checking_account.deposit

        # Valida se o valor minimo de reinvestimento e compativel com o reinvestimento desejado
        if min_reinvest > amount:
            return {'message': _("ERROR! The min reinvestment for this plan is {}").format(min_reinvest)}
        if amount_with_fee > balance:
            return {'message': _("ERROR! You does not have enought balance")}
    
        with transaction.atomic():
            investment.plan_grace_period = grace_period
            investment.amount = amount_with_investment
            investment.status = Investments.STATUS.paid
            investment.membership_fee = membership_fee
            investment.paid_date = timezone.now()
            investment.save()

            if grace_period.grace_period.months > 0:
                start_date = datetime.now() + timedelta(days=1)
                end_date = start_date + relativedelta(months=grace_period.grace_period.months)
                
                Incomes.objects.filter(investment=investment, date__gte=start_date.date(), date__lte=end_date.date()).delete()

                range_dates = list(rrule(DAILY, dtstart=start_date, until=end_date))
                income_amount = (amount_with_investment * (grace_period.income_percent / 100)) * grace_period.grace_period.months
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

            discount_amount = investment_account.deposit - amount_with_fee

            if discount_amount < Decimal('0.00'):
                statement = Statement()
                statement.account = investment_account
                statement.amount = Decimal('0.00') - investment_account.deposit
                statement.type = 'reinvestment'
                statement.description = 'New reinvestment'
                statement.fk = investment.pk
                statement.save()

                investment_account.deposit = Decimal('0.00')
                investment_account.save()
            else:
                statement = Statement()
                statement.account = investment_account
                statement.amount = Decimal('0.00') - amount_with_fee
                statement.type = 'reinvestment'
                statement.description = 'New reinvestment'
                statement.fk = investment.pk
                statement.save()

                investment_account.takeout(amount_with_fee)

            if use_checking and discount_amount < Decimal('0.00'):
                checking_account.takeout(abs(discount_amount))

                statement = Statement()
                statement.account = checking_account
                statement.amount = discount_amount
                statement.type = 'reinvestment'
                statement.description = 'New reinvestment'
                statement.fk = investment.pk
                statement.save()

            investment_account.reserved += amount
            investment_account.save()

            statement = Statement()
            statement.account = investment_account
            statement.amount = amount
            statement.type = 'reinvestment'
            statement.description = 'New reinvestment'
            statement.fk = investment.pk
            statement.save()

            reinvestment = Reinvestments()
            reinvestment.old_invest = reinvestment_old_invest
            reinvestment.new_invest = reinvestment_new_invest
            reinvestment.amount = reinvestment_amount
            reinvestment.amount_before = reinvestment_amount_before
            reinvestment.incomes = reinvestment_incomes
            reinvestment.membership_fee = reinvestment_membership_fee
            reinvestment.investment = investment
            reinvestment.save()

        return {'message': _("Congratulations! Your reinvesting plan was created."), 'redirect': True}


class ReferrerSignupView(SignupView):
    form_class = SignupForm
    template_name = 'investment/signup.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._use_address = False

    def dispatch(self, *args, **kwargs):
        username = self.request.session.get('referral_username', False)
        promoter_username = self.request.GET.get('promoter', 'xfactor')

        if not username:
            username = 'xfactor'

        if promoter_username != 'xfactor':
            username = self.request.GET['promoter']

        self.promoter = Users.objects.get(username=username)
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

        if form.cleaned_data['advisor']:
            referral.advisor = Users.objects.filter(username=form.cleaned_data['advisor'], graduations__type=Graduations._advisor).first()

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
