from django.urls import path
from . import views

urlpatterns = [
    path('', views.case_list, name='case_list'),
    path('nuevo/', views.case_create, name='case_create'),
    path('<int:case_id>/toggle/', views.case_toggle, name='case_toggle'),
]
