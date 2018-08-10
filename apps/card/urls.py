from django.urls import include, path

from . import views

urlpatterns = [
    path('card/update/', views.UpdateCardView.as_view(), name='card>update'),
    path('card/recharge/', views.RechargeView.as_view(), name='card>recharge'),
    path('card/bank-slip/', views.BankSlipView.as_view(), name='card>bank-slip'),
]