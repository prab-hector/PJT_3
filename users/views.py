from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import AttendanceLog, Teammates
from django.contrib.auth.decorators import login_required
from .forms import StorageUpdateForm, ProfileUserUpdateForm
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout as django_logout
import calendar
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
import random
from django.shortcuts import HttpResponse
from .models import PasswordResetOTP
from .forms import ForgotPasswordRequestForm, OTPVerifyForm
from django.urls import reverse
from django.contrib import messages


# CRITICAL FIX: Import your buffer from your hardware/gateway app folder
# Replace 'your_hardware_app_name' with your actual app folder name (e.g., storage, rfid_datacoming, etc.)

def home_dashboard(request):
    today = timezone.localdate()

    # Delete old attendance logs older than the first day of the current month
    first_of_month = today.replace(day=1)
    AttendanceLog.objects.filter(timestamp__date__lt=first_of_month).delete()

    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    attendance_logs = AttendanceLog.objects.select_related('teammate').filter(timestamp__date=selected_date).order_by('timestamp')

    # 2. Fetch incomplete profiles (Auto-created by process_rfid)
    incomplete_profiles = Teammates.objects.filter(is_fully_registered=False).order_by('-date_posted')

    # Admin initials logic
    if request.user.is_authenticated:
        admin_name = request.user.get_full_name() or request.user.username
    else:
        admin_name = "Guest Admin"
    admin_initials = "".join([n[0] for n in admin_name.split() if n])[:2].upper()

    context = {
        'attendance_logs': attendance_logs,
        'selected_date': selected_date,
        'today': today,
        'incomplete_profiles': incomplete_profiles,
        'admin_name': admin_name,
        'admin_initials': admin_initials,
        'user': request.user,
    }
    
    # Fixed typo: 'contex' -> 'context'
    return render(request, 'users/homepg.html', context)

def login(request):
    """
    Authentication View: Renders user portal entry page template layout context.
    """
    return render(request, 'users/login.html')

def set_password(request, pk): # 1. Accept pk as an argument
    # 2. Use pk to fetch only the specific user
    target_user = get_object_or_404(User, pk=pk) 
    
    if request.method == 'POST':
        form = SetPasswordForm(target_user, request.POST) 
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            auth_login(request, user)
            # 3. Redirect using the specific user's pk
            return redirect('edit_profile', pk=user.pk)
    else:
        form = SetPasswordForm(target_user)
        
    return render(request, 'users/set_password.html', {'form': form})


def forgot_password_request(request):
    if request.method == 'POST':
        form = ForgotPasswordRequestForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            teammate = Teammates.objects.filter(rfid_number__iexact=identifier).first()
            user = None
            target_email = None

            if teammate:
                user = teammate.author
                target_email = teammate.email or user.email
            else:
                user = User.objects.filter(username__iexact=identifier).first()
                if user:
                    # try to find teammate linked to user
                    teammate = Teammates.objects.filter(author=user).first()
                    target_email = teammate.email if teammate and teammate.email else user.email

            if not user or not target_email:
                messages.error(request, 'No user or email found for that identifier.')
                return render(request, 'users/forgot_password.html', {'form': form})

            # Invalidate existing OTPs
            PasswordResetOTP.objects.filter(user=user, used=False).update(used=True)

            # Generate OTP
            code = str(random.randint(100000, 999999))
            expires_at = timezone.now() + timedelta(minutes=15)
            otp = PasswordResetOTP.objects.create(user=user, code=code, expires_at=expires_at)

            subject = 'Your OTP for password reset'
            message = f'Your OTP for resetting your password is: {code}. It expires in 15 minutes.'
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_HOST_USER
            try:
                send_mail(subject, message, from_email, [target_email], fail_silently=False)
            except Exception as e:
                messages.error(request, f'Failed to send email: {e}')
                return render(request, 'users/forgot_password.html', {'form': form})

            messages.success(request, 'OTP sent to your email. Please check your inbox.')
            return redirect(reverse('verify_otp', args=[user.pk]))
    else:
        form = ForgotPasswordRequestForm()
    return render(request, 'users/forgot_password.html', {'form': form})


def verify_otp(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code'].strip()
            otp = PasswordResetOTP.objects.filter(user=user, code=code, used=False).order_by('-created_at').first()
            if otp and otp.is_valid():
                otp.used = True
                otp.save()
                # redirect to set_password view
                return redirect('set_password', pk=user.pk)
            else:
                messages.error(request, 'Invalid or expired OTP.')
    else:
        form = OTPVerifyForm()
    return render(request, 'users/verify_otp.html', {'form': form, 'user': user})

@login_required
def logout(request):
    django_logout(request)  # This terminates the active session
    return redirect('homepg')  # This bounces them directly back to the dashboard

def profile(request):
     user_storage_records = Teammates.objects.filter(author = request.user)

     context = {
          'records': user_storage_records
     }
     return render(request, 'users/profile.html',context)

@login_required
def edit_profile(request, pk):
    if request.user.pk != pk:
        return redirect('homepg')

    storage_instance = get_object_or_404(Teammates, author=request.user)
    was_pending_registration = not storage_instance.is_fully_registered

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

            if was_pending_registration:
                today = timezone.localdate()
                attendance_log = AttendanceLog.objects.filter(
                    teammate=storage_item,
                    timestamp__date=today,
                ).order_by('timestamp').first()

                if attendance_log:
                    if attendance_log.status != "Present":
                        attendance_log.status = "Present"
                        attendance_log.save(update_fields=['status'])
                else:
                    attendance_log = AttendanceLog.objects.create(
                        teammate=storage_item,
                        status="Present",
                    )

                try:
                    from data_flow.service import push_attendance_to_sheets
                    push_attendance_to_sheets(attendance_log)
                except Exception as e:
                    print(f"Sync Error: {e}")

            if was_pending_registration:
                messages.success(request, "Profile updated successfully! Attendance marked present.")
            else:
                messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        u_form = ProfileUserUpdateForm(instance=request.user)
        s_form = StorageUpdateForm(instance=storage_instance)
    
    context = {
        'u_form': u_form,
        's_form': s_form,
        'my_storage': storage_instance,
        'user_has_password': request.user.has_usable_password()
    }
    return render(request, 'users/edit_profile.html', context)
