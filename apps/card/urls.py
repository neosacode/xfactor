from django.urls import include, path

from . import views

urlpatterns = [
    path('update-card/', views.UpdateCardView.as_view(), name='card>update'),
]