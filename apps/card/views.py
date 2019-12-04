from decimal import Decimal
from django.db import transaction
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from jsonview.decorators import json_view
from account.decorators import login_required

from exchange_core.models import Accounts, Statement
from exchange_core.rates import CurrencyPrice
from apps.card.forms import CardForm, RechargeForm, BankSlipForm
from apps.card.models import Cards


@method_decorator([login_required, json_view], name='dispatch')
class UpdateCardView(View):
    def post(self, request):
        card_obj = Cards.objects.filter(account__user=request.user).first()
        form = CardForm(request.POST, card=card_obj)

        if card_obj.mothers_name:
            return {}

        if not form.is_valid():
            return {'errors': form.errors}


        card = form.save(commit=False)
        card_obj.birth_date = card.birth_date
        card_obj.mothers_name = card.mothers_name
        card_obj.fathers_name = card.fathers_name
        card_obj.document_1 = request.user.document_1
        card_obj.document_2 = request.user.document_2
        card_obj.name = request.user.name
        card_obj.save()

        return {'success': True}


@method_decorator([login_required, json_view], name='dispatch')
class RechargeView(View):
    def post(self, request):
        account = Accounts.objects.filter(user=request.user, currency__code='BTC', currency__type='checking').first()
        br_account = Accounts.objects.filter(user=request.user, currency__code='BRL').first()
        form = RechargeForm(request.POST, user=request.user)

        if not form.is_valid():
            return {'errors': form.errors}

        usd = CurrencyPrice('coinbase')
        br = CurrencyPrice('mercadobitcoin')
        address = request.user.addresses.first()

        if address and address.country.name.lower() == 'brazil':
            quote = br.to_br(1)
        else:
            quote = usd.to_usd(1)

        quote = quote * Decimal('0.93')
        recharge = form.save(commit=False)
        recharge.quote = quote
        btc_amount = round(recharge.amount / quote, 8)

        if btc_amount > account.deposit:
            form.add_error('amount', _("You does not have enought balance"))
            return {'errors': form.errors}

        with transaction.atomic():
            recharge.amount = btc_amount
            recharge.deposit = account.deposit
            recharge.reserved = account.reserved
            recharge.quote = quote
            recharge.card = Cards.objects.filter(account__user=request.user).first()
            recharge.save()

            account.takeout(btc_amount)
            amount = Decimal('0') - btc_amount
            statement = Statement(account=account, amount=amount, fk=recharge.pk)
            statement.description = 'Card Recharge'
            statement.type = 'card_recharge'
            statement.save()

            card = recharge.card
            card.deposit += recharge.quote_amount
            card.save()

            br_account.to_deposit(recharge.quote_amount)

            return {'message_type':  'success', 'message_text': _("Your recharge has been processed by our team and will be available in your card within 24 hours")}


@method_decorator([login_required, json_view], name='dispatch')
class BankSlipView(View):
    def post(self, request):
        account = Accounts.objects.filter(user=request.user, currency__code='BRL', currency__type='checking').first()
        form = BankSlipForm(request.POST, user=request.user)

        if not form.is_valid():
            return {'errors': form.errors}

        amount = form.cleaned_data['amount']
        if amount > account.deposit:
            form.add_error('amount', _("You does not have enought balance"))
            return {'errors': form.errors}

        with transaction.atomic():
            boleto = form.save(commit=False)
            boleto.card = Cards.objects.filter(account__user=request.user).first()
            boleto.payer_name = request.user.name
            boleto.payer_document = request.user.document_1
            boleto.save()

            account.takeout(amount)
            amount = Decimal('0') - amount
            statement = Statement(account=account, amount=amount, fk=boleto.pk)
            statement.description = 'Bank slip payment'
            statement.type = 'bank_slip_payment'
            statement.save()

            card = boleto.card
            card.deposit -= abs(boleto.amount)
            card.save()

            account.takeout(abs(boleto.amount))

            return {'message_type':  'success', 'message_text': _("Your bank slip has been processed by our team and will be paid within 24 hours")}