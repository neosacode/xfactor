from django.contrib import admin
from django.urls import include, re_path, path
from django.conf import settings

from two_factor.urls import urlpatterns as tf_urls

from .views import SelectAccountView, CheckingAccountView, InvestmentAccountView, MyCardView, RequestCardView


urlpatterns = [
	path('account/select/', SelectAccountView.as_view(), name='xfactor>select-account'),
	path('account/checking/', CheckingAccountView.as_view(), name='xfactor>checking'),
	path('account/investment/', InvestmentAccountView.as_view(), name='xfactor>investment'),
	path('account/my-card/', MyCardView.as_view(), name='xfactor>my-card'),
	path('account/request-card/', RequestCardView.as_view(), name='xfactor>request-card'),
	path('account/raw-logout/', LogoutView.as_view(), name='xfactor>logout'),
]


# Carrega dinamicamente as URLs dos pacotes pertencentes a exchange 
for app_name in settings.INSTALLED_APPS:
	if app_name.startswith('exchange_'):
		urls_path = app_name + '.urls'
		urlpatterns.append(path('', include(urls_path)))

urlpatterns.append(path('', include('apps.investment.urls')))
urlpatterns.append(path('', include('apps.boleto.urls')))