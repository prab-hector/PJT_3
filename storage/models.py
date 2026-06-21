from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Teammates(models.Model):
    """
    Unified User Profile & Hardware Status Table
    """
    name = models.CharField(max_length=30)
    branch = models.CharField(max_length=30)
    email = models.EmailField(max_length=254, null=True, blank=True)
    phone_number = models.CharField(max_length=10)
    domain = models.CharField(max_length=10)
    rfid_number = models.CharField(max_length=8, unique=True, db_index=True)
    year = models.CharField(max_length=30)
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # SYSTEM STATE MANAGER: Tracks if a card profile profile is fully setup or placeholder
    is_fully_registered = models.BooleanField(default=True)

    def __str__(self):
        status_flag = "" if self.is_fully_registered else " [PENDING SUBMISSION]"
        return f"{self.name}{status_flag}"


class AttendanceLog(models.Model):
    """
    Unified System Event Log
    """
    # Links directly to our teammate if known, or leaves blank if an unknown scan happens
    teammate = models.ForeignKey(Teammates, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Stores outcomes like: "Present", "System Mode: Add Users", "Access Denied"
    status = models.CharField(max_length=50, default="Present")

    def __str__(self):
        name = self.teammate.name if self.teammate else f"Unknown ({self.rfid_number})"
        return f"{name} - {self.status} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    

class unregistered_log(models.Model):
    rfid_number = models.CharField(max_length=8)
    timestamp = models.DateTimeField(auto_now_add=True)


