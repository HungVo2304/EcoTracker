from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import EcoAction, EcoGroup, UserProfile


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

ALLOWED_CONTENT_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
]


class EcoActionForm(forms.ModelForm):
    class Meta:
        model = EcoAction
        fields = ["image", "caption"]

        widgets = {
            "image": forms.ClearableFileInput(attrs={
                "accept": "image/jpeg,image/png,image/webp"
            }),
            "caption": forms.TextInput(attrs={
                "placeholder": "Describe your eco action..."
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if not image:
            raise ValidationError("Please upload an image.")

        # Check file size
        if image.size > MAX_UPLOAD_SIZE:
            raise ValidationError("Image size must be under 5MB.")

        # Check file extension
        file_name = image.name.lower()
        if not any(file_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise ValidationError("Only JPG, JPEG, PNG, and WEBP images are allowed.")

        # Check content type
        content_type = getattr(image, "content_type", "")

        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError("Invalid image type. Please upload JPG, PNG, or WEBP.")

        return image

    def clean_caption(self):
        caption = self.cleaned_data.get("caption", "").strip()

        if len(caption) < 5:
            raise ValidationError("Caption must be at least 5 characters long.")

        if len(caption) > 255:
            raise ValidationError("Caption must be 255 characters or less.")

        return caption


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



class AvatarForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["avatar"]

        widgets = {
            "avatar": forms.ClearableFileInput(attrs={
                "accept": "image/jpeg,image/png,image/webp"
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")

        if not avatar:
            return avatar

        if avatar.size > MAX_UPLOAD_SIZE:
            raise ValidationError("Avatar size must be under 5MB.")

        file_name = avatar.name.lower()

        if not any(file_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise ValidationError("Only JPG, JPEG, PNG, and WEBP images are allowed.")

        content_type = getattr(avatar, "content_type", "")

        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError("Invalid avatar type. Please upload JPG, PNG, or WEBP.")

        return avatar