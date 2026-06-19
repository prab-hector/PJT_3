"""
URL configuration for rfid_pjt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
# Update your import line to pull all three necessary views
from rfid_datacoming.views import process_rfid, check_buffer, register_user_submit
from users import views as user_views

urlpatterns = [
    # Django Administrative Panel Portal
    path('admin/', admin.site.urls),

    # 1. HARDWARE GATEWAY ENDPOINTS
    path('api/rfid/process/', process_rfid, name='api-rfid-process'),
    path('api/rfid/check-buffer/', check_buffer, name='api-rfid-check-buffer'),
    path('login/', auth_views.LoginView.as_view(template_name = 'users/login.html'), name = 'login'),
    path('logout/', auth_views.LogoutView.as_view(template_name = 'users/logout.html'), name = 'logout'),
    path('profile/', user_views.profile, name = 'profile'),
    path('register/',user_views.register,name = 'register'),
    path('api/rfid/register-submit/', register_user_submit, name='api-rfid-register-submit'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name = 'users/password_reset.html'), name = 'password_reset'),

    # 2. WEB USER DASHBOARD INTERFACES
    path('', include('users.urls')),
]