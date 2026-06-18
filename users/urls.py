from django.urls import path
from . import views

urlpatterns = [
    path('',views.homepg, name = 'homepg'),
    path('register/',views.register,name = 'register'),
    path('api/rfid/process/', views.process_rfid, name='api-rfid-process'),
]