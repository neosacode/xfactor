from django.views.generic import View
from django.utils.decorators import method_decorator
from jsonview.decorators import json_view
from account.decorators import login_required
from apps.card.forms import CardForm
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