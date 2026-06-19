from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User
from storage.models import Teammates, RFIDLog
from users.models import AttendanceLog
import json

# Global application state to store the card pending registration
REGISTRATION_BUFFER = {}

@csrf_exempt
def check_buffer(request):
    """
    Buffer Status Endpoint: Called by the register.html JavaScript loop 
    every 2 seconds to check if a new card has been tapped on the hardware.
    Also handles POST to clear the registration buffer.
    URL Path: /api/rfid/check-buffer/
    """
    global REGISTRATION_BUFFER
    if request.method == 'POST':
        REGISTRATION_BUFFER.clear()
        return JsonResponse({'status': 'success', 'message': 'Staging buffer cleared.'})
        
    hidden_uid = REGISTRATION_BUFFER.get('temporary_hidden_uid')
    master_scanned = REGISTRATION_BUFFER.get('master_scanned', False)
    master_scanned_at = REGISTRATION_BUFFER.get('master_scanned_at', None)
    
    return JsonResponse({
        'card_staged': bool(hidden_uid),
        'rfid_id': hidden_uid,
        'master_scanned': master_scanned,
        'master_scanned_at': master_scanned_at
    })

@csrf_exempt
def process_rfid(request):
    """
    Core Gateway Endpoint: Receives all raw HTTP POST scan packets from the ESP32 hardware client.
    URL Path: /api/rfid/process/
    """
    global REGISTRATION_BUFFER
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except json.JSONDecodeError:
            print("--- [SERVER ALERT] Received invalid JSON payload layout ---")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)

        if not rfid_uid:
            print("--- [SERVER ALERT] Request rejected: RFID ID string missing ---")
            return JsonResponse({'status': 'error', 'message': 'Missing RFID ID'}, status=400)

        # ---------------------------------------------------------
        # HARDCODED HARDWARE CONTROL CONFIGURATION
        # ---------------------------------------------------------
        ADD_USER_MASTER_UID = "E25B2F45"     # Master Card 1: Triggers addition mode
        DELETE_USER_MASTER_UID = "893997C1"  # Master Card 2: Triggers deletion mode

        # ---- CONDITION A: ADD-USER MASTER SCANNED ----
        if rfid_uid == ADD_USER_MASTER_UID:
            print(f"--- [SYSTEM DETECTED] MASTER CARD FOR ADD DETECTED: {rfid_uid} ---")
            REGISTRATION_BUFFER['master_scanned'] = True
            REGISTRATION_BUFFER['master_scanned_at'] = timezone.now().timestamp()
            REGISTRATION_BUFFER['temporary_hidden_uid'] = None
            return JsonResponse({
                'status': 'system_action', 
                'message': 'Master Card for ADD scanned successfully.'
            }, status=200)

        # ---- CONDITION B: DELETE-USER MASTER SCANNED ----
        if rfid_uid == DELETE_USER_MASTER_UID:
            print(f"--- [SYSTEM DETECTED] MASTER CARD FOR DELETE DETECTED: {rfid_uid} ---")
            REGISTRATION_BUFFER.clear()
            return JsonResponse({
                'status': 'system_action', 
                'message': 'Master Card for DELETE scanned successfully. Buffer cleared.'
            }, status=200)

        # ---- LOGIC FOR STANDARD AND REGISTRATION SCANS ----
        try:
            # Check if this card belongs to an existing teammate profile
            teammate = Teammates.objects.get(rfid_number=rfid_uid)
            
            # Log the normal check-in inside your RFIDLog data tracking system
            RFIDLog.objects.create(uid=rfid_uid)
            
            # Mark their attendance in the AttendanceLog table
            AttendanceLog.objects.create(teammates=teammate, status="Present")
            
            print(f"--- [ATTENDANCE SUCCESS] Card verified! Logged check-in for: {teammate.name} ---")
            return JsonResponse({'status': 'success', 'message': f'Attendance logged for {teammate.name}.'}, status=200)
            
        except Teammates.DoesNotExist:
            # This is an unknown card.
            # ONLY stage it if the master card has been scanned and we are waiting for a new user registration.
            if REGISTRATION_BUFFER.get('master_scanned', False):
                REGISTRATION_BUFFER['temporary_hidden_uid'] = rfid_uid
                REGISTRATION_BUFFER['master_scanned'] = False
                REGISTRATION_BUFFER['master_scanned_at'] = None
                print(f"--- [REGISTRATION STAGED] Unknown Card detected: {rfid_uid}. Staging card into memory buffer ---")
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Unknown card {rfid_uid} successfully staged for registration.',
                    'rfid_id': rfid_uid
                }, status=200)
            else:
                print(f"--- [ACCESS DENIED] Unknown Card scanned but registration mode not active: {rfid_uid} ---")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Card not registered. Attendance not marked.'
                }, status=200)
                
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


@csrf_exempt
def register_user_submit(request):
    """
    Profile Provisioning View: Handles profile submission from web form layout.
    URL Path: /api/rfid/register-submit/
    """
    global REGISTRATION_BUFFER
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
        
    try:
        data = json.loads(request.body)
        username = data.get('name', '').strip()
        branch_name = data.get('department', '').strip()
        phone = data.get('phone', '0000000000').strip()
        academic_year = data.get('year', 'First Year').strip()
        user_email = data.get('email', '').strip() or None

        if not username or not branch_name:
            return JsonResponse({'status': 'error', 'message': 'Name and Department values are required.'}, status=400)
        
        # Extract secret token directly out of internal memory
        hidden_uid = REGISTRATION_BUFFER.get('temporary_hidden_uid')
        
        if not hidden_uid:
            return JsonResponse({'status': 'error', 'message': 'No pending RFID transaction session found. Please scan the RFID card first.'}, status=400)
            
        if request.user.is_authenticated:
            current_author = request.user
        else:
            current_author = User.objects.filter(is_superuser=True).first()
            if not current_author:
                current_author = User.objects.first()
                
        if not current_author:
            return JsonResponse({'status': 'error', 'message': 'Database configuration issue: No system author accounts found.'}, status=500)

        # Commit directly to match the precise database field requirements
        Teammates.objects.create(
            name=username,
            branch=branch_name,
            email=user_email,
            phone_number=phone,
            year=academic_year,
            rfid_number=hidden_uid,
            date_posted=timezone.now(),
            author=current_author
        )
        
        # Flush cache allocation completely to eliminate extraction vulnerabilities
        REGISTRATION_BUFFER.clear()
        
        return JsonResponse({'status': 'success', 'message': 'User registration initialized completely.'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Server Error: {str(e)}'}, status=500)