import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings

def get_spreadsheet_client():
    # Path to your JSON key file stored in settings
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_JSON_KEY_PATH, scope)
    return gspread.authorize(creds)

# Use this when an RFID card is scanned
def push_attendance_to_sheets(log):
    client = get_spreadsheet_client()
    sheet = client.open_by_key('1yd9KGAWrjjazzwoK-T6rWVk5074mm5IkGWbDLYOlwXw').sheet1
    row_data = [
        log.teammate.name if log.teammate else 'Unknown',
        str(log.timestamp.time()),
        str(log.timestamp.date()),
        log.teammate.domain if log.teammate else 'N/A',
        log.teammate.year if log.teammate else 'N/A',
        log.teammate.phone_number if log.teammate else 'N/A',
        log.teammate.email if log.teammate else 'N/A'
    ]
    sheet.append_row(row_data)