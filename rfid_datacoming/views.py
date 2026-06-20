from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User
from storage.models import Teammates, AttendanceLog
import json

# Global state tracking for master card setup window
REGISTRATION_MODE_ACTIVE = False

@csrf_exempt
def check_buffer(request):
    """
    Buffer Status Endpoint: Called by register.html loop every 2 seconds.
    Finds the latest skeleton record created during active registration.
    """
    global REGISTRATION_MODE_ACTIVE
    
    if request.method == 'POST':
        REGISTRATION_MODE_ACTIVE = False
        return JsonResponse({
            'status': 'success', 
            'message': 'Registration buffer cleared.'
        })
        
    # Check database for the temporary placeholder row created by process_rfid
    staged_card = Teammates.objects.filter(name="New Flagged Card User").order_by('-date_posted').first()
    
    if staged_card:
        return JsonResponse({
            'card_staged': True,
            'rfid_id': staged_card.rfid_number,
            'master_scanned': REGISTRATION_MODE_ACTIVE,
            'master_scanned_at': None
        })
        
    return JsonResponse({
        'card_staged': False,
        'rfid_id': None,
        'master_scanned': REGISTRATION_MODE_ACTIVE,
        'master_scanned_at': None
    })

@csrf_exempt
def process_rfid(request):
    """
    Core Gateway Endpoint: Receives all HTTP POST packet streams from ESP32.
    """
    global REGISTRATION_MODE_ACTIVE
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)

        if not rfid_uid:
            return JsonResponse({'status': 'error', 'message': 'Missing RFID ID'}, status=400)

        # Hardcoded Control Master Keys
        ADD_USER_MASTER_UID = "E25B2F45"
        DELETE_USER_MASTER_UID = "893997C1"

        if rfid_uid == ADD_USER_MASTER_UID:
            REGISTRATION_MODE_ACTIVE = True
            return JsonResponse({
                'status': 'system_action', 
                'message': 'Master Card for ADD scanned. Registration window open.'
            }, status=200)

        if rfid_uid == DELETE_USER_MASTER_UID:
            REGISTRATION_MODE_ACTIVE = False
            return JsonResponse({
                'status': 'system_action', 
                'message': 'Master Card for DELETE scanned. Registration mode reset.'
            }, status=200)

        try:
            # Match existing user
            teammate = Teammates.objects.get(rfid_number=rfid_uid)
            AttendanceLog.objects.create(teammates=teammate, status="Present")
            return JsonResponse({
                'status': 'success', 
                'message': f'Attendance logged for {teammate.name}.'
            }, status=200)
            
        except Teammates.DoesNotExist:
            # Save a placeholder row if Master card registration window is open
            if REGISTRATION_MODE_ACTIVE:
                current_author = User.objects.filter(is_superuser=True).first() or User.objects.first()
                if not current_author:
                    return JsonResponse({'status': 'error', 'message': 'No author profiles found.'}, status=500)

                new_teammate = Teammates.objects.create(
                    name="New Flagged Card User",
                    branch="Unassigned",
                    email=None,
                    phone_number="0000000000",
                    year="Unassigned",
                    rfid_number=rfid_uid,
                    date_posted=timezone.now(),
                    author=current_author
                )
                
                REGISTRATION_MODE_ACTIVE = False # Lock window down for stability
                return JsonResponse({
                    'status': 'redirect_ready',
                    'message': 'Card captured inside system database.',
                    'new_user_id': new_teammate.id
                }, status=200)
            else:
                return JsonResponse({'status': 'error', 'message': 'Card not registered.'}, status=200)
                
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@csrf_exempt
def register_user_submit(request):
    """
    Profile Provisioning View: Updates skeleton record with form data.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
        
    try:
        data = json.loads(request.body)
        rfid_uid = data.get('rfid_id', '').strip().upper() # Extracted from payload
        username = data.get('name', '').strip()
        branch_name = data.get('department', '').strip()
        phone = data.get('phone', '0000000000').strip()
        academic_year = data.get('year', 'First Year').strip()
        user_email = data.get('email', '').strip() or None

        if not username or not branch_name or not rfid_uid:
            return JsonResponse({
                'status': 'error', 
                'message': 'Name, Department, and RFID Token UID are required.'
            }, status=400)
            
        # Select the pending profile row 
        teammate = Teammates.objects.filter(rfid_number=rfid_uid, name="New Flagged Card User").first()
        
        if not teammate:
            return JsonResponse({'status': 'error', 'message': 'No pending registration record found.'}, status=404)
            
        # Commit live values over placeholder row fields
        teammate.name = username
        teammate.branch = branch_name
        teammate.phone_number = phone
        teammate.year = academic_year
        teammate.email = user_email
        teammate.save()
            
        return JsonResponse({
            'status': 'success', 
            'message': f'User {username} successfully registered!'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Server Error: {str(e)}'}, status=500)