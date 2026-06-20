from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User
# Verified clean imports directly from your unified storage house app
from storage.models import Teammates, AttendanceLog
import json

# Global application memory variable to track master configuration window state
REGISTRATION_MODE_ACTIVE = False

@csrf_exempt
def check_buffer(request):
    """
    Buffer Status Endpoint: Called by the register.html JavaScript loop 
    every 2 seconds to check if a new card has been tapped on the hardware.
    Also handles POST to clear the registration buffer.
    URL Path: /api/rfid/check-buffer/
    """
    global REGISTRATION_MODE_ACTIVE
    
    if request.method == 'POST':
        REGISTRATION_MODE_ACTIVE = False
        return JsonResponse({
            'status': 'success', 
            'message': 'Registration buffer cleared.'
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
    Core Gateway Endpoint: Receives all raw HTTP POST scan packets from the ESP32 hardware client.
    URL Path: /api/rfid/process/
    """
    global REGISTRATION_MODE_ACTIVE
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except json.JSONDecodeError:
            print("--- [SERVER ALERT] Received invalid JSON payload layout ---")
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid JSON body'
            }, status=400)

        if not rfid_uid:
            print("--- [SERVER ALERT] Request rejected: RFID ID string missing ---")
            return JsonResponse({
                'status': 'error', 
                'message': 'Missing RFID ID'
            }, status=400)

        # ---------------------------------------------------------
        # HARDCODED HARDWARE CONTROL CONFIGURATION
        # ---------------------------------------------------------
        ADD_USER_MASTER_UID = "E25B2F45"     # Master Card 1: Triggers addition mode
        DELETE_USER_MASTER_UID = "893997C1"  # Master Card 2: Triggers deletion mode

        # ---- CONDITION A: ADD-USER MASTER SCANNED ----
        if rfid_uid == ADD_USER_MASTER_UID:
            print(f"--- [SYSTEM DETECTED] MASTER CARD FOR ADD DETECTED: {rfid_uid} ---")
            REGISTRATION_MODE_ACTIVE = True
            return JsonResponse({
                'status': 'system_action', 
                'message': 'Master Card for ADD scanned successfully. Registration window open.'
            }, status=200)

        # ---- CONDITION B: DELETE-USER MASTER SCANNED ----
        if rfid_uid == DELETE_USER_MASTER_UID:
            print(f"--- [SYSTEM DETECTED] MASTER CARD FOR DELETE DETECTED: {rfid_uid} ---")
            REGISTRATION_MODE_ACTIVE = False
            return JsonResponse({
                'status': 'system_action', 
                'message': 'Master Card for DELETE scanned successfully. Registration mode reset.'
            }, status=200)

        # ---- LOGIC FOR STANDARD AND REGISTRATION SCANS ----
        try:
            # Check if this card belongs to an existing teammate profile
            teammate = Teammates.objects.get(rfid_number=rfid_uid)
            
            # Mark their attendance in the AttendanceLog table located within storage
            AttendanceLog.objects.create(teammates=teammate, status="Present")
            
            print(f"--- [ATTENDANCE SUCCESS] Card verified! Logged check-in for: {teammate.name} ---")
            return JsonResponse({
                'status': 'success', 
                'message': f'Attendance logged for {teammate.name}.'
            }, status=200)
            
        except Teammates.DoesNotExist:
            # This is an unknown card.
            # ONLY stage it if the master card has been scanned and we are waiting for a new user registration.
            if REGISTRATION_MODE_ACTIVE:
                
                # Fallback configuration structure to obtain an account creator instance profile
                current_author = User.objects.filter(is_superuser=True).first() or User.objects.first()
                if not current_author:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Database error: No author profiles found.'
                    }, status=500)

                # Instantly drop a skeleton record row entry into the Teammates table database
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
                
                # Deactivate registration window state immediately for security tracking
                REGISTRATION_MODE_ACTIVE = False
                print(f"--- [AUTO REGISTRATION] Card {rfid_uid} recorded permanently as Pending Profile Row ---")
                
                return JsonResponse({
                    'status': 'redirect_ready',
                    'message': 'Card captured inside system database.',
                    'new_user_id': new_teammate.id
                }, status=200)
            else:
                print(f"--- [ACCESS DENIED] Unknown Card scanned but registration mode not active: {rfid_uid} ---")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Card not registered. Attendance not marked.'
                }, status=200)
                
    else:
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid request method'
        }, status=400)


@csrf_exempt
def register_user_submit(request):
    """
    Profile Provisioning View: Handles profile submission from web form layout.
    URL Path: /api/rfid/register-submit/
    """
    global REGISTRATION_MODE_ACTIVE
    
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid request method'
        }, status=400)
        
    try:
        data = json.loads(request.body)
        username = data.get('name', '').strip()
        branch_name = data.get('department', '').strip()
        phone = data.get('phone', '0000000000').strip()
        academic_year = data.get('year', 'First Year').strip()
        user_email = data.get('email', '').strip() or None

        if not username or not branch_name:
            return JsonResponse({
                'status': 'error', 
                'message': 'Name and Department values are required.'
            }, status=400)
            
        return JsonResponse({
            'status': 'success', 
            'message': 'User verification data aligned completely.'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': f'Server Error: {str(e)}'
        }, status=500)