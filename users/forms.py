from django import forms
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator
from users.models import Teammates

class StorageUpdateForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        max_length=30,
        label='Name / Username',
        help_text='This name is used to generate your login username.',
    )
    email = forms.EmailField(
        required=True,
        label='Email',
        help_text='Set your preferred email address here.',
    )
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
        fields = ['name', 'email', 'domain', 'branch', 'phone_number', 'year', 'division', 'about']


