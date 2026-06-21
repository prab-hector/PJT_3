from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator
from storage.models import Teammates
class ProfileUserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username','email']

class StorageUpdateForm(forms.ModelForm):
    
    division = forms.CharField(required=True)
    domain = forms.CharField(required=True)
    branch = forms.CharField(required=True)
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
        # This list ensures ONLY these 5 fields are rendered and processed
        fields = ['division', 'domain', 'branch','phone_number','year']