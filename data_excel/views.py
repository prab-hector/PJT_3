import os
import json
import gspread
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from oauth2client.service_account import ServiceAccountCredentials
from storage.models import AttendanceLog

def export_current_month_on_demand(request):
    if request.method == "POST":
        # Capture the custom tab/sheet name input by the user from the front-end form
        custom_sheet_name = request.POST.get("custom_sheet_name", "").strip()
        
        if not custom_sheet_name:
            messages.error(request, "Please provide a valid name for the sheet.")
            return render(request, "storage/export_form.html")

        # 1. Fetch current month "till-date" runtime context
        now = timezone.localtime(timezone.now())
        start_date = now.date().replace(day=1)  # 1st day of the current month
        end_date = now.date()                  # Today's date

        # 2. Gather records using our unified AttendanceLog model
        logs_to_export = AttendanceLog.objects.filter(
            timestamp__date__range=[start_date, end_date]
        ).select_related('teammates')

        if not logs_to_export.exists():
            messages.warning(request, f"No records found from {start_date} to {end_date}.")
            return render(request, "storage/export_form.html")

        # 3. Establish Secure Google Cloud Connection Channel
        json_string = os.environ.get('GOOGLE_CREDS_JSON_STRING')
        if not json_string:
            messages.error(request, "Server Configuration Error: Missing API keys.")
            return render(request, "storage/export_form.html")

        try:
            creds_dict = json.loads(json_string)
        except json.JSONDecodeError:
            messages.error(request, "Server Configuration Error: Invalid API key format.")
            return render(request, "storage/export_form.html")

        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
        client = gspread.authorize(creds)

        # 4. Access Master Workbook File
        spreadsheet_name = "RFID Attendance Master Sheet"
        try:
            sheet = client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            messages.error(request, f"Spreadsheet '{spreadsheet_name}' not found.")
            return render(request, "storage/export_form.html")

        # 5. Generate or clear the custom named tab
        try:
            worksheet = sheet.worksheet(custom_sheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            # Create a fresh tab with the custom name provided by the user
            worksheet = sheet.add_worksheet(title=custom_sheet_name, rows="1500", cols="4")
        
        worksheet.append_row(["Student Name", "Branch", "RFID UID", "Scan Timestamp"])

        # 6. Matrix Compilation (Fixed Field References)
        rows_to_append = []
        for log in logs_to_export:
            # Safely check if the log entry points to a registered user profile
            has_profile = log.teammates is not None
            
            rows_to_append.append([
                log.teammates.name if has_profile else "Unknown Token",
                log.teammates.branch if has_profile else "N/A",
                log.teammates.rfid_number if has_profile else "UNKNOWN", # Fixed: Extracting card ID from teammate relation
                timezone.localtime(log.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            ])

        # Push payload array to cloud endpoint
        worksheet.append_rows(rows_to_append)

        # 7. Redirect straight to the live updated master sheet link
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.id}/edit#gid={worksheet.id}"
        return redirect(spreadsheet_url)

    # If GET request, just render the simple input form page
    return render(request, "storage/export_form.html")