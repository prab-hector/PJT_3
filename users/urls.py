from django.urls import path
from . import views
from rfid_datacoming.views import process_rfid

urlpatterns = [
    path('',views.home_dashboard, name = 'homepg'),
    path('register/',views.register,name = 'register'),
    path('api/rfid/process/', process_rfid, name='api-rfid-process'),
]