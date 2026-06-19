from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm
from .models import AttendanceLog

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
    # 1. Pull the hidden token from server cache RAM
    hidden_uid = REGISTRATION_BUFFER.get('temporary_hidden_uid')
    
    # 2. Security Wall: Kick them back out to home dashboard if no active hardware session is staged
    if not hidden_uid:
        messages.error(request, "Access Denied: Please tap the Add-User Master Card first.")
        return redirect('homepg') 

    if request.method == 'POST':
        # 3. Securely pass the secret token directly to the form instance constructor
        form = UserRegisterForm(request.POST, rfid_number=hidden_uid)
        if form.is_valid():
            form.save() # Persists User and Teammates entry with zero frontend exposure
            
            # 4. Clear the memory slot completely
            REGISTRATION_BUFFER.pop('temporary_hidden_uid', None)
            
            messages.success(request, "User registered successfully without token leaks!")
            return redirect('homepg')
    else:
        # Pass the token for initial GET initialization tracking
        form = UserRegisterForm(rfid_number=hidden_uid)
        
    return render(request, 'users/register.html', {'form': form})