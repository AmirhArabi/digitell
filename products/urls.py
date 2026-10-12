from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('shop/', views.shop_view, name='shop'),
    path('shop/category/<slug:slug>/', views.shop_view, name='category_detail'),
    path('products/<int:pk>/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('live-search/', views.live_search_view, name='live_search'),
]
