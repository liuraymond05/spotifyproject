from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.contrib.auth.models import User

#Form for login application
class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label='Username')
    password = forms.CharField(widget=forms.PasswordInput)

#Form to create an account
class CustomUserForm(UserCreationForm):
    email = forms.EmailField(max_length=100, help_text='Enter a valid email address.', required=True)
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

#Form to reset your password
class  PasswordResetCustomForm(PasswordResetForm):
    email = forms.EmailField(max_length=100, required=True, widget=forms.EmailInput(attrs={'placeholder': 'Enter your associated email'}), label='')
    username = forms.CharField(max_length=100, label='', widget=forms.TextInput(attrs={'placeholder': 'Enter your username'}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Enter a new password'}), label='')
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password'}), label='')

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError('Passwords do not match, please try again.')
        return cleaned_data