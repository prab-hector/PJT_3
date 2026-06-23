from django.shortcuts import render
import pandas as pd
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
MASTER_DELETE_CARD_ID = "893997C1"  # Admin scans this card to enter delete mode

def _generate_unique_username(base_username):
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{counter}"
        counter += 1
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

        # 0.5. Master Delete Card Logic - Activate delete mode for next scan
        if rfid_uid == MASTER_DELETE_CARD_ID:
            cache.set('delete_mode_active', True, 30)  # 30 second window
            return JsonResponse({
                'status': 'success', 
                'message': 'Delete mode activated. Next card scan will delete today\'s attendance log.',
                'mode': 'delete'
            }, status=200)

        # Check if we're in delete mode
        delete_mode_active = cache.get('delete_mode_active', False)

        # 1. Check if the user is already registered
        teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
        
        if teammate:
            today = timezone.localdate()
            
            # If in delete mode, delete today's attendance log
            if delete_mode_active:
                cache.delete('delete_mode_active')  # Exit delete mode
                
                deleted_count, _ = AttendanceLog.objects.filter(
                    teammate=teammate,
                    timestamp__date=today
                ).delete()
                
                if deleted_count > 0:
                    return JsonResponse({
                        'status': 'success',
                        'message': f'Deleted {deleted_count} attendance log(s) for today',
                        'action': 'deleted'
                    }, status=200)
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'No attendance log found for today to delete',
                    }, status=400)
            
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

            AttendanceLog.objects.create(teammate=teammate, status="Present")
            push_attendance_to_sheets(AttendanceLog.objects.last())
            return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)

        # 2. If unknown, create a new linked User + teammate record
        else:
            if delete_mode_active:
                cache.delete('delete_mode_active')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Cannot delete: Unknown RFID card. User not registered.'
                }, status=400)

            base_username = f"rfid_{rfid_uid}"
            username = _generate_unique_username(base_username)
            email = f"{username}@example.com"

            new_user = User.objects.create_user(username=username, email=email)
            new_user.set_unusable_password()
            new_user.save()

            new_teammate = Teammates.objects.create(
                name="New Student",
                branch="Unassigned",
                phone_number="0000000000",
                year="Year",
                rfid_number=rfid_uid,
                is_fully_registered=False,
                author=new_user
            )

            AttendanceLog.objects.create(teammate=new_teammate, status="Pending registration")
            return JsonResponse({
                'status': 'created',
                'message': 'Profile created and pending registration',
                'user_id': new_user.pk,
                'teammate_id': new_teammate.pk,
            }, status=201)
        
       
            
    return JsonResponse({'status': 'error'}, status=400)