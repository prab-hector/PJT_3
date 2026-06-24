from django.shortcuts import render
import pandas as pd
import random
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from .service import push_attendance_to_sheets
from django.http import JsonResponse
import json
from django.utils import timezone
from users.models import Teammates, AttendanceLog
from django.contrib.auth.models import User
from django.core.cache import cache

MASTER_ENROLL_ID = "E25B2F45"

def _generate_random_username():
    while True:
        username = f"user_{random.randint(1000, 9999)}"
        if not User.objects.filter(username=username).exists():
            return username

@csrf_exempt
def process_rfid(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        rfid_uid = data.get('rfid_id', '').strip().upper()
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'JSON Error'}, status=400)
    
    teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
    
    # 1. Master ID Check
    if rfid_uid == MASTER_ENROLL_ID:
        cache.set('admin_mode_active', True, timeout=70)
        return JsonResponse({'status': 'success', 'message': 'Admin Mode: Scan next card to modify.'})
    
    # 2. Admin Mode (Delete/Create)
    elif cache.get('admin_mode_active'):
        cache.delete('admin_mode_active')
        
        if teammate:
            if teammate.is_fully_registered:
                teammate.author.delete() # Ensure Cascade is set in model
                return JsonResponse({'status': 'success', 'message': 'User deleted.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Cannot delete: User not fully registered.'}, status=400)
        
        else:
            # Create new user logic
            username = _generate_random_username()
            email = f"nli{random.randint(1000,9999)}@gmail.com"
            new_user = User.objects.create_user(username=username, email=email)
            new_user.set_unusable_password()
            new_user.save()
            new_teammate = Teammates.objects.create(
                name=username,
                email=email,
                branch="Unassigned",
                phone_number="0000000000",
                year="Year",
                rfid_number=rfid_uid,
                is_fully_registered=False,
                author=new_user
            )
            return JsonResponse({
                'status': 'created',
                'message': 'Profile created. Scan again after completing profile.',
                'user_id': new_user.pk,
                'teammate_id': new_teammate.pk,
            }, status=201)

    # 3. Regular Attendance Mode
    elif teammate:
        if not teammate.is_fully_registered or teammate.phone_number == "0000000000":
            return JsonResponse({
                'status': 'pending_registration',
                'message': 'Registration pending: complete your profile',
            }, status=200)
        
        today = timezone.localdate()
        if AttendanceLog.objects.filter(teammate=teammate, timestamp__date=today).exists():
            return JsonResponse({
                'status': 'success',
                'message': 'Attendance already marked for today',
                'already_marked': True
            }, status=200)

        new_log = AttendanceLog.objects.create(teammate=teammate, status="Present")
        try:
            push_attendance_to_sheets(new_log)
        except Exception as e:
            print(f"Sync Error: {e}")
        return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)
            
    else:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)