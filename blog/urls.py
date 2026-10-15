from django.urls import path, re_path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.post_list_view, name='post_list'),
    # اسلاگ‌ها فارسی هستند؛ بنابراین از الگوی یونیکد استفاده می‌کنیم.
    re_path(r'^category/(?P<category_slug>[-\w]+)/$', views.post_list_view, name='post_category'),
    re_path(r'^(?P<slug>[-\w]+)/$', views.post_detail_view, name='post_detail'),
]
