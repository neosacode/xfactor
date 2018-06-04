from django.contrib import admin
from django.urls import include, re_path, path
from django.conf import settings

from two_factor.urls import urlpatterns as tf_urls

from . import views

urlpatterns = [
	path('account/statement/', views.StatementView.as_view(), name='core>statement'),

	path('account/select/', views.SelectAccountView.as_view(), name='xfactor>select-account'),
	path('account/checking/', views.CheckingAccountView.as_view(), name='xfactor>checking'),
	path('account/investment/', views.InvestmentAccountView.as_view(), name='xfactor>investment'),
	path('account/my-card/', views.MyCardView.as_view(), name='xfactor>my-card'),
	path('account/request-card/', views.RequestCardView.as_view(), name='xfactor>request-card'),
	path('account/raw-logout/', views.LogoutView.as_view(), name='xfactor>logout'),
	path('account/create-course-subscription/', views.CreateCourseSubscriptionView.as_view(), name='xfactor>create-course-subscription'),
]


# Carrega dinamicamente as URLs dos pacotes pertencentes a exchange 
for app_name in settings.INSTALLED_APPS:
	if app_name.startswith('exchange_'):
		urls_path = app_name + '.urls'
		urlpatterns.append(path('', include(urls_path)))

urlpatterns.append(path('', include('apps.investment.urls')))
urlpatterns.append(path('', include('apps.boleto.urls')))