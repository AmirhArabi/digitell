from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.ticket_list_view, name='list'),
    path('new/', views.ticket_new_view, name='create_form'),
    path('new/save/', views.ticket_create_view, name='create'),
    path('<int:pk>/', views.ticket_detail_view, name='detail'),
    path('<int:pk>/messages/', views.ticket_messages_partial_view, name='messages'),
    path('<int:pk>/reply/', views.ticket_reply_view, name='reply'),
    path('<int:pk>/close/', views.ticket_close_view, name='close'),
]
