from django import forms

class FirstLoginForm(forms.Form):
    email = forms.EmailField(required=True, help_text="Enter your email address")
    new_password = forms.CharField(widget=forms.PasswordInput(), required=True, help_text="Enter a new password")