from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.contrib.auth.models import User

# Form for login application
class LoginForm(forms.Form):
    """
    Form for handling user login by collecting the username and password.

    Fields:
        username (CharField): The username of the user.
        password (CharField): The password of the user (input is hidden for security).

    Methods:
        clean: Optionally, custom validation can be added to check the correctness of the login credentials.
    """
    username = forms.CharField(max_length=100, label='Username')
    password = forms.CharField(widget=forms.PasswordInput)

# Form to create an account
class CustomUserForm(UserCreationForm):
    """
    A form for creating a new user account by providing the username, email, and password.

    Fields:
        username (CharField): The username of the user.
        email (EmailField): The email address of the user (required and validated).
        password1 (CharField): The user's password.
        password2 (CharField): Confirmation of the password (should match password1).

    Meta:
        model: User
        fields: ('username', 'email', 'password1', 'password2')
    """
    email = forms.EmailField(max_length=100, help_text='Enter a valid email address.', required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

# Form to reset your password
class PasswordResetCustomForm(PasswordResetForm):
    """
    A form to reset a user's password by verifying their email, username, and new password.

    Fields:
        email (EmailField): The email address associated with the user's account (required).
        username (CharField): The username associated with the account (required).
        new_password1 (CharField): The new password the user wants to set (input is hidden for security).
        new_password2 (CharField): Confirmation of the new password (input is hidden for security).

    Methods:
        clean: Validates that the new passwords match.
    """
    email = forms.EmailField(max_length=100, required=True, widget=forms.EmailInput(attrs={'placeholder': 'Enter your associated email'}), label='')
    username = forms.CharField(max_length=100, label='', widget=forms.TextInput(attrs={'placeholder': 'Enter your username'}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Enter a new password'}), label='')
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password'}), label='')

    def clean(self):
        """
        Custom validation to ensure that the new passwords match.

        Returns:
            cleaned_data (dict): The cleaned data containing the password information.
            
        Raises:
            ValidationError: If the new passwords do not match, an error is raised.
        """
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError('Passwords do not match, please try again.')
        return cleaned_data