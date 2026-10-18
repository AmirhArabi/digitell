from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('check-phone/', views.check_phone_view, name='check_phone'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('addresses/add-ajax/', views.add_address_ajax_view, name='add_address_ajax'),
    path('favorites/toggle/<int:product_id>/', views.toggle_favorite_view, name='toggle_favorite'),
    path('deposit/', views.deposit_view, name='deposit'),
]
