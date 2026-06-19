from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm
from .models import AttendanceLog
from storage.models import Teammates
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, StorageUpdateForm, ProfileUserUpdateForm

# CRITICAL FIX: Import your buffer from your hardware/gateway app folder
# Replace 'your_hardware_app_name' with your actual app folder name (e.g., storage, rfid_datacoming, etc.)
from rfid_datacoming.views import REGISTRATION_BUFFER

def home_dashboard(request):
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


def register(request):
    # 1. Pull the hidden token and master status from server cache RAM
    hidden_uid = REGISTRATION_BUFFER.get('temporary_hidden_uid')
    master_scanned = REGISTRATION_BUFFER.get('master_scanned', False)
    
    # 2. Security Wall: Kick them back out to home dashboard if no active hardware session is staged/active
    if not hidden_uid and not master_scanned:
        messages.error(request, "Access Denied: Please tap the Add-User Master Card first.")
        return redirect('homepg') 

    if request.method == 'POST':
        # 3. Securely pass the secret token directly to the form instance constructor
        form = UserRegisterForm(request.POST, rfid_number=hidden_uid)
        if form.is_valid():
            form.save() # Persists User and Teammates entry with zero frontend exposure
            
            # 4. Clear the memory slot completely
            REGISTRATION_BUFFER.clear()
            
            messages.success(request, "User registered successfully without token leaks!")
            return redirect('profile')
    else:
        # Pass the token for initial GET initialization tracking
        form = UserRegisterForm(rfid_number=hidden_uid)
        
    return render(request, 'users/register.html', {'form': form})

def login(request):
    return render(request, 'users/login.html')

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

