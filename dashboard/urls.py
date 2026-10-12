from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview_view, name='overview'),
    path('products/', views.product_list_view, name='products'),
    path('products/create/', views.product_create_view, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit_view, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete_view, name='product_delete'),
    path('orders/', views.order_list_view, name='orders'),
    path('orders/<int:pk>/status/', views.order_update_status_view, name='order_status'),
    path('settings/', views.settings_view, name='settings'),
]
