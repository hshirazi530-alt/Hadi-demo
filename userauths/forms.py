from django import forms
from django.contrib.auth.forms import UserCreationForm
from userauths.models import User, Profile


class UserRegisterForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "نام کاربری را وارد کنید:"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "ایمیل را وارد کنید:"}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "رمز را وارد کنید:"}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "تایید رمز:"}))
    class Meta:
        model = User
        fields = ['username', 'email']



class ProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        required=False,
        max_length=200,
        label="نام کامل",
        widget=forms.TextInput(attrs={"placeholder": "نام و نام خانوادگی"}),
    )
    bio = forms.CharField(
        required=False,
        max_length=200,
        label="دربارهٔ من",
        widget=forms.TextInput(attrs={"placeholder": "دربارهٔ من"}),
    )
    phone = forms.CharField(
        required=False,
        max_length=200,
        label="شمارهٔ تماس",
        widget=forms.TextInput(
            attrs={"placeholder": "شمارهٔ تماس", "type": "tel", "inputmode": "tel"}
        ),
    )

    class Meta:
        model = Profile
        fields = ['full_name', 'image', 'bio', 'phone']
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "name"}
            ),
            "bio": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "tel",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }