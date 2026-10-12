from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.post_list_view, name='post_list'),
    path('category/<slug:category_slug>/', views.post_list_view, name='post_category'),
    path('<slug:slug>/', views.post_detail_view, name='post_detail'),
]
