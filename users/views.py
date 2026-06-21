from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from storage.models import AttendanceLog
from storage.models import Teammates
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views
from .forms import StorageUpdateForm, ProfileUserUpdateForm
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout as django_logout
from datetime import datetime
import calendar
from django.contrib.auth import login
from django.contrib.auth.models import User


# CRITICAL FIX: Import your buffer from your hardware/gateway app folder
# Replace 'your_hardware_app_name' with your actual app folder name (e.g., storage, rfid_datacoming, etc.)

def home_dashboard(request):
    # 1. Fetch recent logs
    recent_scans = AttendanceLog.objects.select_related('teammate').order_by('-timestamp')[:10]
    
    # 2. Fetch incomplete profiles (Auto-created by process_rfid)
    incomplete_profiles = Teammates.objects.filter(is_fully_registered=False).order_by('-date_posted')

    # Admin initials logic
    if request.user.is_authenticated:
        admin_name = request.user.get_full_name() or request.user.username
    else:
        admin_name = "Guest Admin"
    admin_initials = "".join([n[0] for n in admin_name.split() if n])[:2].upper()

    context = {
        'recent_scans': recent_scans,
        'incomplete_profiles': incomplete_profiles, # New data for your template
        'admin_name': admin_name,
        'admin_initials': admin_initials,
    }
    
    # Fixed typo: 'contex' -> 'context'
    return render(request, 'users/homepg.html', context)

def login(request):
    """
    Authentication View: Renders user portal entry page template layout context.
    """
    return render(request, 'users/login.html')

def set_password(request, pk):
    # 1. Fetch the user you want to set the password for
    target_user = get_object_or_404(User, pk=pk)
    print(f"DEBUG: set_password called with id={pk}")
    
    if request.method == 'POST':
        # 2. Pass 'target_user' to the form, NOT 'request.user'
        form = SetPasswordForm(target_user, request.POST)
        if form.is_valid():
            # 3. Save the password for the target_user
            user = form.save()
            # 4. Log the user in so they have a session
            login(request, user)
            # 5. Redirect to edit_profile using the target_user's teammate record
            return redirect('edit_profile', pk=user.teammates.pk)
    else:
        # Pass 'target_user' here as well
        form = SetPasswordForm(target_user)
        
    return render(request, 'users/set_password.html', {'form': form})

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
def edit_profile(request, pk):
    storage_instance = get_object_or_404(Teammates, pk=pk)

    if request.method == 'POST':
        # Check if the user has a password; if not, block the update
        if not request.user.has_usable_password():
            messages.warning(request, "You must set a password before updating your profile.")
            return redirect('homepg')

        u_form = ProfileUserUpdateForm(request.POST, instance=request.user)
        s_form = StorageUpdateForm(request.POST, instance=storage_instance)
    
        if u_form.is_valid() and s_form.is_valid():
            u_form.save()
            storage_item = s_form.save(commit=False)
            storage_item.is_fully_registered = True 
            storage_item.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        u_form = ProfileUserUpdateForm(instance=request.user)
        s_form = StorageUpdateForm(instance=storage_instance)
    
    context = {
        'u_form': u_form,
        's_form': s_form,
        'user_has_password': request.user.has_usable_password()
    }
    return render(request, 'users/edit_profile.html', context)


@login_required
def reset_password(request):
    return redirect('password_reset')