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
        body = request.body.decode('utf-8')
        data = json.loads(body) if body else {}
    except Exception:
        data = request.POST.dict()

    rfid_uid = data.get('rfid_id', '').strip().upper()
    if not rfid_uid:
        return JsonResponse({'status': 'error', 'message': 'Missing rfid_id'}, status=400)

    teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
    
    # 1. Master ID Check
    if rfid_uid == MASTER_ENROLL_ID:
        cache.set('admin_mode_active', True, timeout=70)
        return JsonResponse({'status': 'success', 'message': 'Admin Mode: Scan next card to modify.'})
    
    # 2. Admin Mode (Delete/Create)
    if cache.get('admin_mode_active'):
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
    











# ****************************************************************************************
# views.py code
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

# Create your views here.

# Use this for downloading the Excel report
def export_Attendance_Log(request):
    selected_date = request.GET.get('date')
    # Fetch data from SQLite
    logs = AttendanceLog.objects.filter(timestamp__date=selected_date)
    # Convert QuerySet to DataFrame
    data = [{
        'Name': log.teammate.name if log.teammate else 'Unknown',
        'Time': str(log.timestamp.time()),
        'Date': str(log.timestamp.date()),
        'Domain': log.teammate.domain if log.teammate else 'N/A',
        'Year': log.teammate.year if log.teammate else 'N/A',
        'Phone number': log.teammate.phone_number if log.teammate else 'N/A',
        'Email': log.teammate.email if log.teammate else 'N/A'
    } for log in logs]
    df = pd.DataFrame(data)
    # Generate Excel response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Attendance_{selected_date}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
    return response


# Define your Master IDs here
MASTER_ENROLL_ID = "E25B2F45"
 # Admin scans this card to enter delete mode

def _generate_random_username():
    while True:
        username = f"user_{random.randint(1000, 9999)}"
        if not User.objects.filter(username=username).exists():
            return username

@csrf_exempt
def process_rfid(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'JSON Error'}, status=400)

        # 0. Master Enroll Card Logic
        if rfid_uid == MASTER_ENROLL_ID:
            return JsonResponse({'status': 'success', 'message': 'Enrollment Gateway Open'}, status=200)

        # 1. Check if the user is already registered
        teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
        
        if teammate:
            if not teammate.is_fully_registered or teammate.phone_number == "0000000000":
                return JsonResponse({
                    'status': 'pending_registration',
                    'message': 'Registration pending: complete your profile with a valid phone number before attendance can be recorded.',
                }, status=200)

            today = timezone.localdate()
            
            # Normal mode - add attendance
            same_day_log_exists = AttendanceLog.objects.filter(
                teammate=teammate,
                timestamp__date=today
            ).exists()

            if same_day_log_exists:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Attendance already marked for today',
                    'already_marked': True
                }, status=200)

            # Create specific log instance and sync to Google Sheets
            new_log = AttendanceLog.objects.create(teammate=teammate, status="Present")
            try:
                push_attendance_to_sheets(new_log)
            except Exception as e:
                print(f"Sync Error: {e}")
            
            return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)

        # 2. If unknown, create a new linked User + teammate record
        else:
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
                'message': 'Profile created and pending registration. Scan again after completing profile.',
                'user_id': new_user.pk,
                'teammate_id': new_teammate.pk,
            }, status=201)
            
    return JsonResponse({'status': 'error'}, status=400)



# *********************************************************************************************

























































MASTER_ENROLL_ID = "E25B2F45"
 # Admin scans this card to enter delete mode

def _generate_random_username():
    while True:
        username = f"user_{random.randint(1000, 9999)}"
        if not User.objects.filter(username=username).exists():
            return username

@csrf_exempt
def process_rfid(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'JSON Error'}, status=400)

        # 0. Master Enroll Card Logic
        if rfid_uid == MASTER_ENROLL_ID:
            return JsonResponse({'status': 'success', 'message': 'Enrollment Gateway Open'}, status=200)

        # 1. Check if the user is already registered
        teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
        
        if teammate:
            if not teammate.is_fully_registered or teammate.phone_number == "0000000000":
                return JsonResponse({
                    'status': 'pending_registration',
                    'message': 'Registration pending: complete your profile with a valid phone number before attendance can be recorded.',
                }, status=200)

            today = timezone.localdate()
            
            # Normal mode - add attendance
            same_day_log_exists = AttendanceLog.objects.filter(
                teammate=teammate,
                timestamp__date=today
            ).exists()

            if same_day_log_exists:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Attendance already marked for today',
                    'already_marked': True
                }, status=200)

            # Create specific log instance and sync to Google Sheets
            new_log = AttendanceLog.objects.create(teammate=teammate, status="Present")
            try:
                push_attendance_to_sheets(new_log)
            except Exception as e:
                print(f"Sync Error: {e}")
            
            return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)

        # 2. If unknown, create a new linked User + teammate record
        else:
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
                'message': 'Profile created and pending registration. Scan again after completing profile.',
                'user_id': new_user.pk,
                'teammate_id': new_teammate.pk,
            }, status=201)
            
    return JsonResponse({'status': 'error'}, status=400)