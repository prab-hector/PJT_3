from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm
from storage.models import AttendanceLog
from storage.models import Teammates
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views
from .forms import UserRegisterForm, StorageUpdateForm, ProfileUserUpdateForm
from django.contrib.auth import logout as django_logout
from datetime import datetime
import calendar

# CRITICAL FIX: Import your buffer from your hardware/gateway app folder
# Replace 'your_hardware_app_name' with your actual app folder name (e.g., storage, rfid_datacoming, etc.)

def home_dashboard(request):

    today = datetime.today() # Resolves to June 2026
    
    # Calculate boundaries
    first_day_of_month = today.replace(day=1).strftime('%Y-%m-%d')
    
    # Cap selection at today's active date (no future days)
    max_selectable_day = today.strftime('%Y-%m-%d')

    context = {
        'min_date': first_day_of_month, # '2026-06-01'
        'max_date': max_selectable_day,   # '2026-06-20'
    }

    recent_scans = AttendanceLog.objects.select_related('teammates').order_by('-timestamp')[:10]

    if request.user.is_authenticated:
        admin_name = request.user.get_full_name() or request.user.username
    else:
        admin_name = "Guest Admin"

    admin_initials = "".join([n[0] for n in admin_name.split() if n])[:2].upper()

    context = {
        'recent_scans': recent_scans,
        'admin_name': admin_name,
        'admin_initials': admin_initials,
    }
    return render(request, 'users/homepg.html', context)

def register(request, teammate_id=None):
    # 1. Safely locate the skeleton database profile created by the hardware tap
    profile_instance = None
    hidden_uid = None
    
    if teammate_id:
        profile_instance = get_object_or_404(Teammates, id=teammate_id)
        hidden_uid = profile_instance.rfid_number
    else:
        # Fallback security if someone hits /register/ without a skeleton row ID
        messages.error(request, "Access Denied: No active card registration session found.")
        return redirect('homepg')

    # 2. Handle Form Submission
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, rfid_number=hidden_uid)
        if form.is_valid():
            saved_user = form.save()
            
            # Update the existing placeholder row state to active
            if profile_instance:
                profile_instance.is_fully_registered = True
                profile_instance.save()
                
            messages.success(request, f"Profile info for {saved_user.username} finalized successfully!")
            return redirect('homepg')
            
    # 3. Handle Initial Form Render (GET Request)
    else:
        initial_data = {}
        if profile_instance:
            initial_data = {
                'branch': profile_instance.branch,
                'year': profile_instance.year,
                'phone_number': profile_instance.phone_number
            }
        form = UserRegisterForm(initial=initial_data, rfid_number=hidden_uid)
        
    return render(request, 'users/register.html', {'form': form})

def login(request):
    """
    Authentication View: Renders user portal entry page template layout context.
    """
    return render(request, 'users/login.html')

def login(request):
    return render(request, 'users/login.html')

@login_required
def logout(request):
    django_logout(request)  # This terminates the active session
    return redirect('homepg')  # This bounces them directly back to the dashboard

@login_required
def profile(request):
     user_storage_records = Teammates.objects.filter(author = request.user)

     context = {
          'records': user_storage_records
     }
     return render(request, 'user/profile.html',context)

@login_required
def edit_profile(request):
    # Fetch the specific active storage row item for this user
    storage_instance = Teammates.objects.filter(author=request.user).first()

    if request.method == 'POST':
        u_form = ProfileUserUpdateForm(request.POST, instance=request.user)
        s_form = StorageUpdateForm(request.POST, instance=storage_instance)

        if u_form.is_valid() and s_form.is_valid():
            u_form.save()
            
            # Catch instance creation fallback safety check
            storage_item = s_form.save(commit=False)
            if not storage_item.pk:
                storage_item.author = request.user
            storage_item.save()
            
            messages.success(request, "Your profile fields have been updated successfully!")
            return redirect('profile')
    else:
        u_form = ProfileUserUpdateForm(instance=request.user)
        s_form = StorageUpdateForm(instance=storage_instance)

    context = {
        'u_form': u_form,
        's_form': s_form
    }
    return render(request, 'user/edit_profile.html', context)

@login_required
def reset_password(request):
    return redirect('password_reset')