import os
import json
import calendar
from django.core.management.base import BaseCommand
from django.shortcuts import render, redirect
from django.utils import timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from storage.models import AttendanceLog

class Command(BaseCommand):
    help = "Exports previous month's logs on the 1st day of a new month and clears local row space."

    def handle(self, *args, **options):
        # 1. Fetch current runtime context
        now = timezone.localtime(timezone.now())
        today = now.date()
        
        # LOGIC FIX: Target execution strictly on the 1st morning of the new month
        if today.day != 1:
            self.stdout.write(self.style.WARNING(
                f"Skipping execution. Today ({today}) is day {today.day}. Automation runs only on Day 1."
            ))
            return

        # Calculate exact start and end bounds of the complete previous month
        # Example: If today is July 1, target_date becomes June 30
        target_date = today - timezone.timedelta(days=1)
        start_date = target_date.replace(day=1)
        end_date = target_date

        # 2. Gather records for the entire previous month (Optimized to prevent N+1 queries)
        logs_to_export = AttendanceLog.objects.filter(
            timestamp__date__range=[start_date, end_date]
        ).select_related('teammates') # Crucial performance patch

        if not logs_to_export.exists():
            self.stdout.write(self.style.WARNING("No records found to export."))
            return

        # 3. Establish Google Cloud Connection API Channel Securely via Environment Variable
        json_string = os.environ.get('GOOGLE_CREDS_JSON_STRING')
        
        if not json_string:
            self.stdout.write(self.style.ERROR(
                "Configuration Error: 'GOOGLE_CREDS_JSON_STRING' environment variable is missing!"
            ))
            return

        try:
            # Parse the single-line string securely back into a dictionary object
            creds_dict = json.loads(json_string)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse environment JSON string: {e}"))
            return
        
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Authenticate using dictionary credentials directly instead of a file path
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
        client = gspread.authorize(creds)

        # 4. Access Master Workbook File 
        spreadsheet_name = "RFID Attendance Master Sheet"
        try:
            sheet = client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            self.stdout.write(self.style.ERROR(f"Spreadsheet '{spreadsheet_name}' not found."))
            return

        # 5. DYNAMIC MONTH TAB GENERATION: NLI attendance list of month {Month Name}
        previous_month_name = target_date.strftime('%B')  # Accurately grabs the month name that just ended
        worksheet_title = f"NLI attendance list of month {previous_month_name}"
        
        try:
            worksheet = sheet.worksheet(worksheet_title)
            worksheet.clear()
            worksheet.append_row([ "Name","date","Domain","timestamp","phone_number","Email"])
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=worksheet_title, rows="1500", cols="4")
            worksheet.append_row(["Name","date","Domain","timestamp","phone_number","Email"])

        # 6. Matrix compilation
        rows_to_append = []
        for log in logs_to_export:
            has_profile = hasattr(log, 'teammates') and log.teammates is not None
            rows_to_append.append([
                log.teammates.name if has_profile else "Unknown Token",
                log.teammates.branch if has_profile else "N/A",
                log.uid,
                timezone.localtime(log.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            ])

        # Push payload array to cloud endpoint 
        worksheet.append_rows(rows_to_append)
        self.stdout.write(self.style.SUCCESS(f"Successfully archived log spreadsheet tab: {worksheet_title}"))

        # 7. Local clean data space recovery optimization 
        count, _ = logs_to_export.delete()
        self.stdout.write(self.style.SUCCESS(f"Storage Optimization: Safely dropped {count} log rows from your live database file."))