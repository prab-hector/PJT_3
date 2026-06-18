from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Teammates(models.Model):
    name = models.CharField(max_length=30)
    branch = models.CharField(max_length=30)
    email = models.EmailField(max_length=254, null=True, blank=True)
    phone_number = models.CharField(max_length=10, null=False, blank=False)
    year = models.CharField(max_length=30)
    rfid_number = models.CharField(max_length=8)
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name
    

class AttendanceLog(models.Model):
    Teammates = models.ForeignKey(Teammates, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="Present")
    
