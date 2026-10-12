from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('faq/', views.faq_view, name='faq'),
    path('contact/', views.contact_view, name='contact'),
    path('installment/', views.installment_view, name='installment'),
]
