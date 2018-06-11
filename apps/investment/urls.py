from django.urls import path

from . import views


urlpatterns = [
    path('investment/plans/', views.PlansView.as_view(), name='investment>plans'),
    path('investment/create-investment/', views.CreateInvestmentView.as_view(), name='investment>create-investment'),
    path('investment/create-reinvestment/', views.CreateReinvestmentView.as_view(), name='investment>create-reinvestment'),
    path('investment/cancel-investment/', views.CancelNoFidelityPlanView.as_view(), name='investment>cancel-investment'),
    path('investment/reinvestment/', views.ReinvestmentView.as_view(), name='investment>reinvestment'),
    path('investment/signup/', views.ReferrerSignupView.as_view(), name='investment>signup'),
    path('investment/get-plan-lacks/', views.GetPlanLacksView.as_view(), name='investment>get-plan-lacks'),
    path('investment/my-customers/', views.MyCustomersView.as_view(), name='investment>my-customers'),
    path('investment/credit-line/', views.CreditLineView.as_view(), name='investment>credit-line'),
    
]
