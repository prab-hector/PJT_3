from django.db import models
from storage.models import Teammates
# Create your models here.
class AttendanceLog(models.Model):
    teammates = models.ForeignKey(Teammates, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="Present")
    
    def __str__(self):
        return f"{self.teammate.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"