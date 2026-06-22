# data_excel/services.py
from users.models import AttendanceLog
import pandas as pd
from django.conf import settings
from pathlib import Path
import os
from datetime import datetime


def get_attendance_for_date(target_date):
    """Return a list of dicts for attendance on a given date."""
    logs = AttendanceLog.objects.filter(timestamp__date=target_date).select_related('teammate')
    data = [
        {
            "Name": (log.teammate.name if log.teammate else 'Unknown'),
            "Date": log.timestamp.date(),
            "Time": log.timestamp.time(),
            "Domain": (log.teammate.domain if log.teammate else ''),
            "Branch": (log.teammate.branch if log.teammate else ''),
            "Phone": (log.teammate.phone_number if log.teammate else ''),
            "Email": (log.teammate.email if log.teammate else ''),
            "Status": log.status,
        }
        for log in logs
    ]
    return data


def generate_monthly_report(year: int, month: int, save_dir: str = None, delete_after: bool = True):
    """Generate an Excel report for a given month/year and optionally delete those logs.

    - Saves an Excel file named Attendance_YYYY_MM.xlsx in `save_dir` or settings.BASE_DIR/reports.
    - Returns the path to the saved file.
    - If `delete_after` is True the AttendanceLog records for that month are deleted after successful write.
    """
    # Resolve save dir
    base = Path(save_dir) if save_dir else Path(settings.BASE_DIR) / 'reports'
    os.makedirs(base, exist_ok=True)

    logs = AttendanceLog.objects.filter(timestamp__year=year, timestamp__month=month).select_related('teammate')
    if not logs.exists():
        return None

    rows = []
    for log in logs:
        rows.append({
            'ID': log.id,
            'Name': log.teammate.name if log.teammate else 'Unknown',
            'RFID': log.teammate.rfid_number if log.teammate else 'N/A',
            'Branch': log.teammate.branch if log.teammate else 'N/A',
            'Date': log.timestamp.date(),
            'Time': log.timestamp.time(),
            'Status': log.status,
        })

    df = pd.DataFrame(rows)
    filename = f"Attendance_{year}_{str(month).zfill(2)}.xlsx"
    file_path = base / filename

    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')

    # If asked, delete logs for that month to save storage
    if delete_after:
        # Only delete attendance logs, not teammates
        logs.delete()

    return str(file_path)