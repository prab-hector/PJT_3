from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User
from storage.models import Teammates, RFIDLog
import json

# Global application states to track separate card processes
# Note: For multi-worker production setups, migrate these to Django Cache (Redis/Memcached)
REGISTRATION_BUFFER = {}
REGISTRATION_MODE_ACTIVE = False
DELETE_MODE_ACTIVE = False

@csrf_exempt
def process_rfid(request):
    """
    Core Gateway Endpoint: Receives all raw HTTP POST scan packets from the ESP32 hardware client.
    URL Path: /api/rfid/process/
    """
    global REGISTRATION_MODE_ACTIVE, DELETE_MODE_ACTIVE, REGISTRATION_BUFFER
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
        
    try:
        data = json.loads(request.body)
        rfid_uid = data.get('rfid_id', '').strip().upper()
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)

    if not rfid_uid:
        return JsonResponse({'status': 'error', 'message': 'Missing RFID ID'}, status=400)

    # ---------------------------------------------------------
    # HARDCODED HARDWARE CONTROL CONFIGURATION
    # ---------------------------------------------------------
    ADD_USER_MASTER_UID = "E25B2F45"     # Master Card 1: Triggers addition mode
    DELETE_USER_MASTER_UID = "893997C1"  # Master Card 2: Triggers deletion mode

    # ---- CONDITION A: ADD-USER MASTER SCANNED ----
    if rfid_uid == ADD_USER_MASTER_UID:
        REGISTRATION_MODE_ACTIVE = True  
        DELETE_MODE_ACTIVE = False       # Safety flush override
        return JsonResponse({
            'status': 'system_action', 
            'message': 'Add-User Master Card detected. Next unknown scan will be buffered.'
        })

    # ---- CONDITION B: DELETE-USER MASTER SCANNED ----
    if rfid_uid == DELETE_USER_MASTER_UID:
        DELETE_MODE_ACTIVE = True        
        REGISTRATION_MODE_ACTIVE = False # Safety flush override
        return JsonResponse({
            'status': 'system_action', 
            'message': 'Delete-User Master Card armed. Scan an existing card to remove it completely.'
        })

    # ---- ROUTE 1: ACTIVE DELETION PROCESSING ----
    if DELETE_MODE_ACTIVE:
        DELETE_MODE_ACTIVE = False       # Immediately disarm to prevent chain deletions
        try:
            teammate = Teammates.objects.get(rfid_number=rfid_uid)
            target_name = teammate.name
            teammate.delete()
            return JsonResponse({'status': 'success', 'message': f'Profile for {target_name} wiped successfully.'})
        except Teammates.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Scanned token not found in database. Deletion aborted.'}, status=404)

    # ---- ROUTE 2: ACTIVE ATTENDANCE VALIDATION ----
    try:
        teammate = Teammates.objects.get(rfid_number=rfid_uid)
        
        # Reset staging flag if an already registered card is presented
        REGISTRATION_MODE_ACTIVE = False 
        
        # Log the event inside your RFIDLog system table
        RFIDLog.objects.create(uid=rfid_uid)
        
        return JsonResponse({'status': 'success', 'message': f'Attendance logged for {teammate.name}.'})
        
    except Teammates.DoesNotExist:
        # ---- ROUTE 3: SECURE REGISTRATION PROCESSING ----
        if REGISTRATION_MODE_ACTIVE:
            REGISTRATION_MODE_ACTIVE = False # Clear staging state arm
            
            # Keep raw token cached strictly inside private server memory
            REGISTRATION_BUFFER['temporary_hidden_uid'] = rfid_uid
            
            # Security Rule: Trigger redirect to client without transferring the raw UID token block
            return JsonResponse({
                'status': 'registration_trigger',
                'message': 'Secure registration slot staged. Forwarding to entry interface.',
                'redirect_url': '/dashboard/register/'
            }, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': 'Unknown card scanned. Access Denied.'}, status=401)


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
            return JsonResponse({'status': 'error', 'message': 'No pending RFID transaction session found.'}, status=400)
            
        # Determine relational user profile object instance requirement for 'author' field
        if request.user.is_authenticated:
            current_author = request.user
        else:
            # Fallback handling strategy: link to primary administrative account if scanned from unauthenticated client panel
            current_author = User.objects.filter(is_superuser=True).first()
            if not current_author:
                # Absolute safety fallback case if no superuser exists yet
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
        
        # CRITICAL RECOVERY STATE: Flush cache allocation immediately to eliminate extraction vulnerabilities
        REGISTRATION_BUFFER.pop('temporary_hidden_uid', None)
        
        return JsonResponse({'status': 'success', 'message': 'User registration initialized completely.'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Server Error: {str(e)}'}, status=500)