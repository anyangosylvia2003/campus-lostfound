from django.urls import path
from . import views

app_name = 'items'

urlpatterns = [
    path('', views.home, name='home'),
    path('items/', views.item_list, name='list'),
    path('items/new/', views.item_create, name='create'),
    path('items/<int:pk>/', views.item_detail, name='detail'),
    path('items/<int:pk>/edit/', views.item_edit, name='edit'),
    path('items/<int:pk>/delete/', views.item_delete, name='delete'),
    path('items/<int:pk>/resolve/', views.item_resolve, name='resolve'),
    path('items/<int:pk>/contact/', views.contact_owner, name='contact'),
    path('my-items/', views.my_items, name='my_items'),
]
