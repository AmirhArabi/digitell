from django.urls import path, re_path
from . import views

app_name = 'products'

urlpatterns = [
    path('shop/', views.shop_view, name='shop'),
    # اسلاگ محصولات و دسته‌بندی‌ها فارسی هستند؛ بنابراین از الگوی یونیکد استفاده می‌کنیم.
    re_path(r'^shop/category/(?P<slug>[-\w]+)/$', views.shop_view, name='category_detail'),
    re_path(r'^products/(?P<pk>\d+)/(?P<slug>[-\w]+)/$', views.product_detail_view, name='product_detail'),
    path('live-search/', views.live_search_view, name='live_search'),
]
