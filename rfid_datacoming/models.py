from django.db import models

# Create your models here.
class RFIDLog(models.Model):
    uid = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UID: {self.uid} at {self.timestamp}"
