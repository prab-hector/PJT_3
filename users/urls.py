from django.urls import path
from . import views

from django.urls import path
from . import views

urlpatterns = [
    # Main landing page dashboard tracking real-time logs
    path('', views.home_dashboard, name='homepg'),
    path('profile/', views.profile, name='profile'),
    
    # Secure teammate data entry onboarding registration portal
    path('register/', views.register, name='register'), 
]