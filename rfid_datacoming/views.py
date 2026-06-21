from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User
from storage.models import Teammates, AttendanceLog
import json

@csrf_exempt
def process_rfid(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'JSON Error'}, status=400)

        # 1. Check if the user is already registered
        teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
        
        if teammate:
            # Mark attendance
            AttendanceLog.objects.create(teammate=teammate, status="Present")
            return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)

        # 2. If unknown, auto-create skeleton profile (The new workflow)
        else:
            current_author = User.objects.first() # Or handle as needed
            new_teammate = Teammates.objects.create(
                name="New Student",
                branch="Unassigned",
                phone_number="0000000000",
                year="Year",
                rfid_number=rfid_uid,
                is_fully_registered=False, # Use this to filter on your dashboard
                author=current_author
            )
            return JsonResponse({'status': 'created', 'message': 'Profile Created, Pending Edit'}, status=201)
            
    return JsonResponse({'status': 'error'}, status=400)