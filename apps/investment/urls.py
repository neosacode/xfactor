from django.urls import path

from . import views


urlpatterns = [
    path('investment/plans/', views.PlansView.as_view(), name='investment>plans'),
    path('investment/my-plans/', views.MyPlansView.as_view(), name='investment>my-plans'),
    path('investment/plan-selected/', views.PlanSelectedView.as_view(), name='investment>plan-selected'),
    path('investment/cancel-investment/', views.CancelNoFidelityPlanView.as_view(), name='investment>cancel-investment'),
    path('investment/signup/', views.ReferrerSignupView.as_view(), name='investment>signup'),
    
]
