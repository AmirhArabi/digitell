from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('addresses/add-ajax/', views.add_address_ajax_view, name='add_address_ajax'),
    path('favorites/toggle/<int:product_id>/', views.toggle_favorite_view, name='toggle_favorite'),
]
