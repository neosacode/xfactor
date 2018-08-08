from django import forms
from django.utils.translation import ugettext_lazy as _
from apps.card import models
from exchange_core.mixins import RequiredFieldsMixin


class CardForm(RequiredFieldsMixin, forms.ModelForm):
    class Meta:
        model = models.Cards
        fields = ['number', 'birth_date', 'mothers_name', 'fathers_name']
        fields_required = ['number', 'birth_date', 'mothers_name', 'fathers_name']

    def __init__(self, *args, **kwargs):
        self.card = kwargs.pop('card')
        super().__init__(*args, **kwargs)

    def clean_number(self):
        number = self.cleaned_data['number']
        number = ''.join(n for n in number if n.isdigit())
        if len(number) != 16:
            raise forms.ValidationError(_("Card number must have 16 digits"))
        if self.card.number != number:
            raise forms.ValidationError(_("Card not found in our system"))
        return number[:10] + '123456'
