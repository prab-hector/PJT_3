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
    year = forms.CharField(required=True, max_length=30, initial="First Year")
    division = forms.CharField(required=True, max_length=20)
    domain = forms.CharField(required=True, max_length=30)

    class Meta:
        model = User
        fields = ['username', 'email']

    # Custom initializer to securely inject the RFID token from the view layer
    def __init__(self, *args, **kwargs):
        self.rfid_number = kwargs.pop('rfid_number', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            if not self.rfid_number:
                raise forms.ValidationError("No active hardware RFID staging session found.")
            
            # Commit metadata to database along with the hidden token string
            Teammates.objects.create(
                author=user,
                name=user.username,
                email=user.email,
                branch=self.cleaned_data['branch'],
                phone_number=self.cleaned_data['phone_number'],
                year=self.cleaned_data['year'],
                rfid_number=self.rfid_number  # Injected securely behind the scenes
            )
            
        return user
    
class ProfileUserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email']

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
        fields = ['email', 'division', 'domain', 'branch','phone_number','year',]