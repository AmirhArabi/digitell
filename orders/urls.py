from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/coupon/', views.apply_coupon_view, name='apply_coupon'),
    path('payment/<str:order_number>/', views.mock_payment_view, name='mock_payment'),
    path('success/<str:order_number>/', views.order_success_view, name='order_success'),
    path('invoice/<str:order_number>/pdf/', views.order_invoice_pdf_view, name='order_invoice_pdf'),
    path('tracking/', views.order_tracking_view, name='order_tracking'),
]
