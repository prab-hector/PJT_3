from django.urls import path
from . import views

urlpatterns = [
    # Main landing page dashboard view tracking real-time logs
    # URL: https://nli.pythonanywhere.com/
    path('', views.home_dashboard, name='homepg'),
    path('login/', views.login, name = 'login').
    
    # Secure blind student data entry onboarding portal
    # URL: https://nli.pythonanywhere.com/register/
    path('register/', views.register, name='register'),
]