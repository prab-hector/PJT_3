import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings

def get_spreadsheet_client():
    # Path to your JSON key file stored in settings
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_JSON_KEY_Path, scope)
    return gspread.authorize(creds)

# Use this when an RFID card is scanned
def push_attendance_to_sheets(log):
    client = get_spreadsheet_client()
    sheet = client.open_by_key('1yd9KGAWrjjazzwoK-T6rWVk5074mm5IkGWbDLYOlwXw').sheet1
    row_data = [
        log.teammate.name if log.teammate else 'Unknown',      # A: Name
        str(log.timestamp.time()),                             # B: Reporting Time
        str(log.timestamp.date()),                             # C: Date
        log.teammate.domain if log.teammate else 'N/A',        # D: Domain
        log.teammate.year if log.teammate else 'N/A',          # E: Year
        log.teammate.phone_number if log.teammate else 'N/A',  # F: Phone number
        log.teammate.email if log.teammate else 'N/A'
    ]
    sheet.append_row(row_data)