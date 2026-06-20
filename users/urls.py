
from django.urls import path
from . import views

urlpatterns = [
    # Main landing page dashboard tracking real-time logs
    path('', views.home_dashboard, name='homepg'),
    path('profile/', views.profile, name='profile'),
    
    # Secure teammate data entry onboarding registration portal
    path('register/', views.register, name='register'), 
    path('register/<int:teammate_id>/', views.register, name='register'),
]
