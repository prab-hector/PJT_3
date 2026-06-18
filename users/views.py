from django.shortcuts import render, redirect
from .forms import UserRegisterForm
# Create your views here.
from django.contrib.auth.decorators import login_required
from .models import AttendanceLog  # Assuming an AttendanceLog handles the check-ins

@login_required
def home_dashboard(request):
    # Fetch today's records sorted by the latest scan time
    recent_scans = AttendanceLog.objects.select_related('teammate').order_by('-scan_time')[:10]
    
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
            user = form.save()  # Saves the user to the database# Logs the new user in on the spot
            return redirect('homepg')
    else:
        # This handles the GET request when a user first visits the page
        form = UserRegisterForm()
        
    # This return statement must be outside the if/else conditions
    return render(request, 'user/register.html', {'form': form})