from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from .models import AttendanceLog  # Assuming AttendanceLog handles the check-ins

def home_dashboard(request):
    # Fixed: Changed '-scan_time' to '-timestamp' to match the model field
    recent_scans = AttendanceLog.objects.select_related('teammates').order_by('-timestamp')[:10]

    # Retrieve the logged-in Admin's details directly from the request session
    admin_name = request.user.get_full_name() or request.user.username
    admin_initials = "".join([n[0] for n in admin_name.split() if n])[:2].upper()

    context = {
        'recent_scans': recent_scans,
        'admin_name': admin_name,
        'admin_initials': admin_initials,
    }
    return render(request, 'homepg.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()  # Saves both the User and corresponding Teammates entry
            return redirect('homepg')
    else:
        form = UserRegisterForm()
        
    return render(request, 'user/register.html', {'form': form})