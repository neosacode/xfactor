from django.conf.urls import url
from django.urls import re_path, path, include

from . import views

urlpatterns = [
    path('boleto/pay', views.PayView.as_view(), name='boleto>pay'),
    path('boleto/create', views.CreateView.as_view(), name='boleto>create')
]