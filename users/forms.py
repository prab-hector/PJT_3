from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator
from users.models import Teammates
class ProfileUserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username','email']

class StorageUpdateForm(forms.ModelForm):
    name = forms.CharField(required=True, max_length=30)
    domain = forms.CharField(required=True)
    branch = forms.CharField(required=True)
    division = forms.CharField(required=False, max_length=30)
    about = forms.CharField(required=False, widget=forms.Textarea)
    phone_number = forms.CharField(
        required=True,
        validators=[
            RegexValidator(r'^\d+$', message="Phone number must contain only numbers."),
            MinLengthValidator(10, message="Phone number must be exactly 10 digits long."), 
            MaxLengthValidator(10, message="Phone number must be exactly 10 digits long.") 
        ],
        widget=forms.TextInput(attrs={'placeholder': 'Enter 10-digit number'})
    )
    year = forms.CharField(required=False, max_length=30)

    class Meta:
        model = Teammates
        # This list ensures only valid teammate fields are rendered and processed
        fields = ['name', 'domain', 'branch', 'phone_number', 'year', 'division', 'about']


class ForgotPasswordRequestForm(forms.Form):
    identifier = forms.CharField(
        required=True,
        help_text="Enter your username or RFID number to receive an OTP by email."
    )


class OTPVerifyForm(forms.Form):
    code = forms.CharField(required=True, max_length=6, min_length=4)