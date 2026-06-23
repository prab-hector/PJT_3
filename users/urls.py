from django.urls import path
from . import views

urlpatterns = [
    # Main landing page dashboard tracking real-time logs
    path('', views.home_dashboard, name='homepg'),
    path('profile/',views.profile, name='profile'),
    path('profile/<int:pk>/edit/', views.edit_profile, name='edit_profile'),
    path('set_password/<int:pk>/', views.set_password, name='set_password'),
    path('forgot-password/', views.forgot_password_request, name='forgot_password'),
    path('verify-otp/<int:pk>/', views.verify_otp, name='verify_otp'),
    
    # Secure teammate data entry onboarding registration portal
]
