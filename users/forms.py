from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator 
from storage.models import Teammates

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True) 
    
    phone_number = forms.CharField(
        required=True,
        validators=[
            RegexValidator(r'^\d+$', message="Phone number must contain only numbers."),
            MinLengthValidator(10, message="Phone number must be exactly 10 digits long."), 
            MaxLengthValidator(10, message="Phone number must be exactly 10 digits long.") 
        ],
        widget=forms.TextInput(attrs={'placeholder': 'Enter 10-digit number'})
    )
    
    branch = forms.CharField(required=True, max_length=30)
    year = forms.CharField(required=False, max_length=30)
    division = forms.CharField(required=True, max_length=20)
    domain = forms.CharField(required=True, max_length=30)
    rfid_number = forms.CharField(required=True,max_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email'] 

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            
            from storage.models import Teammates
            Teammates.objects.create(
                author=user,
                name=user.username,
                branch=self.cleaned_data.get('branch'),
                division=self.cleaned_data.get('division'),
                domain=self.cleaned_data.get('domain'),
                year=self.cleaned_data.get('year'),
                rfid_number = self.cleaned_data.get('rfid_num'),
                phone_number=self.cleaned_data.get('phone_number')
            )
        return user

