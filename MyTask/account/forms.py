from django import forms

class UserUpdateForm(forms.Form):
    username = forms.CharField(max_length=255, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(max_length=128, required=False, widget=forms.PasswordInput)
