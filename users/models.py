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
    division = models.CharField(max_length=30, null=True, blank=True)
    domain = models.CharField(max_length=10)
    rfid_number = models.CharField(max_length=8, unique=True, db_index=True)
    year = models.CharField(max_length=30)
    about = models.TextField(blank=True)
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # SYSTEM STATE MANAGER: Tracks if a card profile profile is fully setup or placeholder
    is_fully_registered = models.BooleanField(default=False)

    def __str__(self):
        status_flag = "" if self.is_fully_registered else " [PENDING SUBMISSION]"
        return f"{self.name}{status_flag}"


class AttendanceLog(models.Model):
    # Links directly to our teammate if known, or leaves blank if an unknown scan happens
    teammate = models.ForeignKey(Teammates, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Stores outcomes like: "Present", "System Mode: Add Users", "Access Denied"
    status = models.CharField(max_length=50, default="Present")
class UnregisteredLog(models.Model):
    rfid_number = models.CharField(max_length=8)
    timestamp = models.DateTimeField(auto_now_add=True)

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone
        return (not self.used) and (self.expires_at >= timezone.now())

    def __str__(self):
        return f"OTP for {self.user.username} - {'used' if self.used else 'active'}"


