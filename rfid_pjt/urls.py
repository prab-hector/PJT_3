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
from rfid_datacoming.views import process_rfid  # Direct cross-app view import

urlpatterns = [
    # Django Administrative Panel Portal
    path('admin/', admin.site.urls),
    
    # 1. HARDWARE GATEWAY ENDPOINT
    # Target URL for ESP32: https://nli.pythonanywhere.com/api/rfid/process/
    path('api/rfid/process/', process_rfid, name='api-rfid-process'),
    
    # 2. WEB USER DASHBOARD INTERFACES
    # Automatically hooks up all paths configured within the users app folder
    path('', include('users.urls')),
]