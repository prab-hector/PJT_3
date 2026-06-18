from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Teammates
import json

# Global application states to track special card processes
# Note: For production systems, use Django Cache (Redis/Memcached) instead of global variables
REGISTRATION_BUFFER = {}
DELETE_MODE_ACTIVE = False

@csrf_exempt
def process_rfid(request):
    global DELETE_MODE_ACTIVE, REGISTRATION_BUFFER
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
        
    try:
        data = json.loads(request.body)
        rfid_uid = data.get('rfid_id', '').strip().upper()
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)
        
    if not rfid_uid:
        return JsonResponse({'status': 'error', 'message': 'Missing RFID ID'}, status=400)

    # Hardcoded System Configuration Tags
    MASTER_CARD_UID = "E25B2F45"  # Replace with actual Master Card UID
    DELETION_CARD_UID = "893997C1"  # Replace with actual Deletion Card UID

    # ---- MODE 1: DELETION HANDLING ----
    if rfid_uid == DELETION_CARD_UID:
        DELETE_MODE_ACTIVE = True
        return JsonResponse({
            'status': 'system_action', 
            'message': 'Deletion mode armed. Scan target card to delete completely.'
        })

    if DELETE_MODE_ACTIVE:
        # Clear the flag immediately to only delete the single next card
        DELETE_MODE_ACTIVE = False
        
        try:
            # Query the database from your Teammates app/class
            teammate = Teammates.objects.get(rfid_number=rfid_uid)
            teammate.delete()
            return JsonResponse({'status': 'success', 'message': f'Record for UID {rfid_uid} deleted successfully.'})
        except Teammates.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Target UID not found in database. Deletion canceled.'})

    # ---- MODE 2: MASTER CARD HANDLING & REGISTRATION FLOW ----
    if rfid_uid == MASTER_CARD_UID:
        return JsonResponse({
            'status': 'system_action', 
            'message': 'Master Card tapped. Dashboard alerted. Present unregistered card.'
        })

    # Check if the scanned card exists inside the Teammates database class
    try:
        teammate = Teammates.objects.get(rfid_number=rfid_uid)
        
        # ---- MODE 3: STANDARD ATTENDANCE RECORDING ----
        # Assuming you have an Attendance tracking class/model linked to Teammates
        # Attendance.objects.create(teammate=teammate, timestamp=timezone.now())
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Attendance successfully logged for {teammate.name}.'
        })
        
    except Teammates.DoesNotExist:
        # Save the unknown UID globally so your dashboard registration page can fetch it auto-filled
        REGISTRATION_BUFFER['last_unregistered_uid'] = rfid_uid
        
        return JsonResponse({
            'status': 'registration_trigger',
            'message': 'User does not exist. Forwarding profile to dashboard registration wizard.',
            'redirect_url': '/dashboard/register/',
            'captured_uid': rfid_uid
        }, status=200)