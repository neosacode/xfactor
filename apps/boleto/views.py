from decimal import Decimal
from datetime import datetime

from django.views.generic import TemplateView
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.http import JsonResponse
from django.db import transaction
from django.utils.decorators import method_decorator
from account.decorators import login_required

from exchange_core.models import Accounts

from .models import Boletos


@method_decorator([login_required], name='dispatch')
class PayView(TemplateView):
    template_name = 'boleto/pay.html'

    def get(self, request):
        real_account = Accounts.objects.get(currency__symbol='BRL', user=request.user)
        boletos = Boletos.objects.filter(card__account__user=request.user)
        return render(request, self.template_name,
                      {'page_title': _("Services > Bank Slip"), 'page_icon': 'fa fa-barcode',
                       'real_account': real_account, 'boletos': boletos})


@method_decorator([login_required], name='dispatch')
class CreateView(TemplateView):
    def post(self, request):
        status = 'success'
        message = _("Your bank slip payment request was created")

        try:
            with transaction.atomic():
                real_account = Accounts.objects.get(currency__symbol='BRL', user=request.user)
                amount = Decimal(request.POST['amount'])
                barcode = ''.join([c for c in request.POST['barcode'] if c.isdigit()])

                if Boletos.objects.filter(barcode=barcode).exists():
                    raise Exception(_("This bank slip is already registered in our system"))

                if real_account.deposit < amount:
                    raise Exception(_("Insufficient funds"))

                boleto = Boletos()
                boleto.barcode = barcode
                boleto.bank_name = request.POST['bank_name']
                boleto.amount = amount
                boleto.expiration_date = datetime.strptime(request.POST['expiration_date'], '%d%m%Y')
                boleto.checksum = request.POST['checksum']
                boleto.user = request.user
                boleto.payer_name = request.POST['payer_name']
                boleto.payer_document = request.POST['payer_document']
                boleto.save()

                real_account.deposit -= amount
                real_account.reserved += amount
                real_account.save()
        except Exception as e:
            status = 'error'
            message = str(e)

        return JsonResponse({'status': status, 'message': message})
