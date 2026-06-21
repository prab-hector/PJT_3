# data_excel/services.py
from storage.models import AttendanceLog # Adjust import based on your actual storage model
import pandas as pd

def get_attendance_for_date(target_date):
    # 1. Query the database
    logs = AttendanceLog.objects.filter(timestamp__date=target_date).select_related('teammates')

    # 2. Process data into a list of dictionaries (or a DataFrame)
    data = [
        {
            "Name": log.teammates.name,
            "Date": log.timestamp.date(),
            "timestamp": log.timestamp.time(),
            "Domain": log.teammates.domain,
            "branch": log.teammates.branch,
            "Phone": log.teammates.phone_number,
            "Email": log.teammates.email,
        }
        for log in logs
    ]
    return data           