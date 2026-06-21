import os
import json
import gspread
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from oauth2client.service_account import ServiceAccountCredentials
from django.contrib.admin.views.decorators import staff_member_required
from storage.models import AttendanceLog, Teammates
import pandas as pd

@staff_member_required
def generate_report(request):
    selected_date = request.GET.get('date') # Get date from your JS picker
    # Query AttendanceLog matching the date
    logs = AttendanceLog.objects.filter(timestamp__date=selected_date)

    # Prepare data list with all requested fields
    data = [{
        'Name': log.teammates.name,
        'Date': log.timestamp.date(),
        'Time': log.timestamp.time(),
        'Year': log.teammates.year,
        'Domain': log.teammates.domain,
        'Division': log.teammates.division,
        'Phone': log.teammates.phone_number,
        'Email': log.teammates.email
    } for log in logs]

    # Send to a temporary sheet or display as a JSON response for the frontend
    # ...