# data_excel/services.py
from users.models import AttendanceLog # Adjust import based on your actual storage model
import pandas as pd

def get_attendance_for_date(target_date):
    # 1. Query the database
    logs = AttendanceLog.objects.filter(timestamp__date=target_date).select_related('teammate')

    # 2. Process data into a list of dictionaries (or a DataFrame)
    data = [
        {
            "Name": log.teammate.name,
            "Date": log.timestamp.date(),
            "timestamp": log.timestamp.time(),
            "Domain": log.teammate.domain,
            "branch": log.teammate.branch,
            "Phone": log.teammate.phone_number,
            "Email": log.teammate.email,
        }
        for log in logs
    ]
    return data           