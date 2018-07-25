from django.urls import include, path
from exchange_core.utils import generate_patterns

from . import views

urlpatterns = [
    path('hi/<username>/', views.HiView.as_view(), name='xfactor>hi'),

    path('account/statement/', views.StatementView.as_view(), name='core>statement'),
    path('account/withdraw-income/', views.IncomesWithdrawView.as_view(), name='core>withdraw-income'),
    path('financial/payments/', views.PaymentsView.as_view(), name='financial>payments'),

    path('account/select/', views.SelectAccountView.as_view(), name='xfactor>select-account'),
    path('account/checking/', views.CheckingAccountView.as_view(), name='xfactor>checking'),
    path('account/investment/', views.InvestmentAccountView.as_view(), name='xfactor>investment'),
    path('account/my-card/', views.MyCardView.as_view(), name='xfactor>my-card'),
    path('account/request-card/', views.RequestCardView.as_view(), name='xfactor>request-card'),
    path('account/raw-logout/', views.LogoutView.as_view(), name='xfactor>logout'),
    path('account/create-course-subscription/', views.CreateCourseSubscriptionView.as_view(), name='xfactor>create-course-subscription'),
    path('account/create-advisor-subscription/', views.CreateAdvisorSubscriptionView.as_view(), name='xfactor>create-advisor-subscription'),
    path('autologin-917293874928asd12397123asd8132/', views.AutoLoginView.as_view(), name='xfactor>autologin'),

    path('', include('apps.investment.urls')),
    path('', include('apps.boleto.urls')),
    path('', include('apps.card.urls')),
]

# Dynamic loads the exchange urls
urlpatterns = generate_patterns(urlpatterns)
