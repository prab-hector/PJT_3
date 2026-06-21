from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Teammates, AttendanceLog
from django.contrib.auth.models import User

# Define your Master IDs here
MASTER_ENROLL_ID = "YOUR_MASTER_ENROLL_ID" 
MASTER_DELETE_ID = "YOUR_MASTER_DELETE_ID"

@csrf_exempt
def process_rfid(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'JSON Error'}, status=400)

        # 0. Master Card Logic
        if rfid_uid == MASTER_DELETE_ID:
            # Logic: If scanned card exists, delete it
            teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
            if teammate:
                teammate.delete()
                return JsonResponse({'status': 'success', 'message': 'User Deleted'}, status=200)
            return JsonResponse({'status': 'error', 'message': 'Card not found to delete'}, status=404)

        if rfid_uid == MASTER_ENROLL_ID:
            return JsonResponse({'status': 'success', 'message': 'Enrollment Gateway Open'}, status=200)

        # 1. Check if the user is already registered
        teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
        
        if teammate:
            # Mark attendance
            AttendanceLog.objects.create(teammate=teammate, status="Present")
            return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)

        # 2. If unknown, only create if the logic allows (or simply create)
        else:
            current_author = User.objects.first() 
            new_teammate = Teammates.objects.create(
                name="New Student",
                branch="Unassigned",
                phone_number="0000000000",
                year="Year",
                rfid_number=rfid_uid,
                is_fully_registered=False,
                author=current_author
            )
            return JsonResponse({'status': 'created', 'message': 'Profile Created, Pending Edit'}, status=201)
            
    return JsonResponse({'status': 'error'}, status=400)