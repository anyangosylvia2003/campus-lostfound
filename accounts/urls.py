from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/',   views.register,             name='register'),
    path('profile/',    views.profile,               name='profile'),
    path('email-log/',  views.email_log_dashboard,   name='email_log'),
]
