from django.shortcuts import render
import pandas as pd
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .service import get_attendance_for_date
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from users.models import Teammates, AttendanceLog
from django.contrib.auth.models import User

# Create your views here.


@staff_member_required
def export_custom_date_view(request):
    selected_date = request.GET.get('date')
    
    # Call the service
    data = get_attendance_for_date(selected_date)
    
    # If no data, handle it
    if not data:
        return HttpResponse("No records found for this date.")

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Generate Excel response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Attendance_{selected_date}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
    return response


# Define your Master IDs here
MASTER_ENROLL_ID = "YOUR_MASTER_ENROLL_ID"

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

        # 1. Check if the user is already registered
        teammate = Teammates.objects.filter(rfid_number=rfid_uid).first()
        
        if teammate:
            # Mark attendance
            AttendanceLog.objects.create(teammate=teammate, status="Present")
            return JsonResponse({'status': 'success', 'message': 'Attendance Marked'}, status=200)

        # 2. If unknown, create a new linked User + teammate record
        else:
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