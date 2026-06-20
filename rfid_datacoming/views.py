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
    
    if request.method == 'POST':
        REGISTRATION_MODE_ACTIVE = False
        Teammates.objects.filter(name="New Flagged Card User").delete()
        return JsonResponse({'status': 'success', 'message': 'Buffer cleared cleanly.'})
        
    staged_card = Teammates.objects.filter(name="New Flagged Card User").order_by('-date_posted').first()
    
    if staged_card:
        return JsonResponse({
            'card_staged': True,
            'rfid_id': staged_card.rfid_number,
            'master_scanned': True
        })
        
    return JsonResponse({
        'card_staged': False,
        'rfid_id': None,
        'master_scanned': REGISTRATION_MODE_ACTIVE
    })

@csrf_exempt
def process_rfid(request):
    global REGISTRATION_MODE_ACTIVE
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_id', '').strip().upper()
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Body Parse Error'}, status=400)

        if not rfid_uid:
            return JsonResponse({'status': 'error', 'message': 'Empty UID received'}, status=400)

        ADD_MASTER = "E25B2F45"
        REMOVE_MASTER = "893997C1"

        if rfid_uid == ADD_MASTER:
            REGISTRATION_MODE_ACTIVE = True
            Teammates.objects.filter(name="New Flagged Card User").delete()
            return JsonResponse({'status': 'success', 'message': 'Staging gate active.'}, status=200)

        if rfid_uid == REMOVE_MASTER:
            REGISTRATION_MODE_ACTIVE = False
            Teammates.objects.filter(name="New Flagged Card User").delete()
            return JsonResponse({'status': 'success', 'message': 'Staging gate closed.'}, status=200)

        try:
            teammate = Teammates.objects.get(rfid_number=rfid_uid)
            if teammate.name == "New Flagged Card User":
                return JsonResponse({'status': 'waiting', 'message': 'Profile registration form pending.'}, status=200)
                
            AttendanceLog.objects.create(teammates=teammate, status="Present")
            return JsonResponse({'status': 'success', 'message': f'Welcome {teammate.name}'}, status=200)
            
        except Teammates.DoesNotExist:
            if REGISTRATION_MODE_ACTIVE:
                current_author = User.objects.filter(is_superuser=True).first() or User.objects.first()
                
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
                return JsonResponse({'status': 'success', 'message': 'Target token captured.'}, status=200)
            else:
                return JsonResponse({'status': 'denied', 'message': 'Card Unknown.'}, status=200)
                
    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=400)

@csrf_exempt
def register_user_submit(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method Denied'}, status=400)
        
    try:
        # Added flexible decoding to handle both JSON payloads and serialized form bodies seamlessly
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        rfid_uid = data.get('rfid_id', '').strip().upper()
        username = data.get('name', '').strip()
        branch_name = data.get('department', '').strip()
        phone = data.get('phone', '0000000000').strip()
        academic_year = data.get('year', 'First Year').strip()
        user_email = data.get('email', '').strip() or None

        if not username or not branch_name or not rfid_uid:
            return JsonResponse({'status': 'error', 'message': 'Required profile registration fields are empty'}, status=400)
            
        teammate = Teammates.objects.filter(rfid_number=rfid_uid, name="New Flagged Card User").first()
        
        if not teammate:
            return JsonResponse({'status': 'error', 'message': 'No staging slot active matching this card token.'}, status=404)
            
        teammate.name = username
        teammate.branch = branch_name
        teammate.phone_number = phone
        teammate.year = academic_year
        teammate.email = user_email
        teammate.save()
            
        return JsonResponse({'status': 'success', 'message': 'Profile provisioned successfully.'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)