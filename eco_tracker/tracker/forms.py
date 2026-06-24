from django import forms
from .models import EcoAction, EcoGroup
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class EcoActionForm(forms.ModelForm):
    class Meta:
        model = EcoAction
        fields = ["image", "caption", "category"]

        widgets = {
            "caption": forms.TextInput(attrs={
                "placeholder": "Describe your eco action..."
            }),
        }


class EcoGroupForm(forms.ModelForm):
    class Meta:
        model = EcoGroup
        fields = ["name"]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter group name..."
            }),
        }



class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]