from django.contrib import admin
from django.urls import include, re_path, path
from django.conf import settings

from two_factor.urls import urlpatterns as tf_urls

urlpatterns = []


# Carrega dinamicamente as URLs dos pacotes pertencentes a exchange 
for app_name in settings.INSTALLED_APPS:
	if app_name.startswith('exchange_'):
		urls_path = app_name + '.urls'
		urlpatterns.append(path('', include(urls_path)))