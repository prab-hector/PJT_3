from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User
from storage.models import Teammates, AttendanceLog
import json

REGISTRATION_MODE_ACTIVE = False

@csrf_exempt
def check_buffer(request):
    global REGISTRATION_MODE_ACTIVE
    staged_card = Teammates.objects.filter(name="New Flagged Card User").order_by('-date_posted').first()
    if staged_card:
        return JsonResponse({'card_staged': True, 'rfid_id': staged_card.rfid_number, 'master_scanned': True})
    return JsonResponse({'card_staged': False, 'rfid_id': None, 'master_scanned': REGISTRATION_MODE_ACTIVE})

@csrf_exempt
def process_rfid(request):
    global REGISTRATION_MODE_ACTIVE
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'JSON Error'}, status=400)

        ADD_MASTER = "E25B2F45"
        REMOVE_MASTER = "893997C1"

        if rfid_uid == ADD_MASTER:
            REGISTRATION_MODE_ACTIVE = True
            Teammates.objects.filter(name="New Flagged Card User").delete()
            return JsonResponse({'status': 'success', 'message': 'Add Mode Open'}, status=200)

        if rfid_uid == REMOVE_MASTER:
            REGISTRATION_MODE_ACTIVE = False
            Teammates.objects.filter(name="New Flagged Card User").delete()
            return JsonResponse({'status': 'success', 'message': 'Remove Mode Open'}, status=200)

        # Check if the user is already registered in the system
        teammate = Teammates.objects.filter(rfid_number=rfid_uid).exclude(name="New Flagged Card User").first()
        if teammate:
            AttendanceLog.objects.create(teammates=teammate, status="Present")
            return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)

        # If it's a new card and Add Mode is active, create the temporary skeleton entry
        if REGISTRATION_MODE_ACTIVE:
            current_author = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if not current_author:
                current_author = User.objects.create_user(username='admin_system', password='SystemPassword123')
            
            Teammates.objects.filter(name="New Flagged Card User").delete()
            Teammates.objects.create(
                name="New Flagged Card User",
                branch="Unassigned",
                phone_number="0000000000",
                year="First Year",
                rfid_number=rfid_uid,
                date_posted=timezone.now(),
                author=current_author
            )
            REGISTRATION_MODE_ACTIVE = False
            return JsonResponse({'status': 'success', 'message': 'Card Staged'}, status=200)
            
        return JsonResponse({'status': 'denied', 'message': 'Unknown Card'}, status=200)
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def register_user_submit(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
            username = data.get('name', '').strip()
            branch_name = data.get('department', '').strip()

            teammate = Teammates.objects.filter(rfid_number=rfid_uid, name="New Flagged Card User").first()
            if teammate:
                teammate.name = username
                teammate.branch = branch_name
                teammate.save()
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)