from django import forms
from core.models import Address, ProductReview
from userauths.models import User


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ("address", "mobile")
        labels = {
            "address": "نشانی کامل",
            "mobile": "شمارهٔ تماس",
        }
        widgets = {
            "address": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "street-address"}
            ),
            "mobile": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "tel",
                    "autocomplete": "tel",
                    "inputmode": "tel",
                }
            ),
        }


class AccountDetailsForm(forms.Form):
    first_name = forms.CharField(
        required=False,
        max_length=150,
        label="نام",
        widget=forms.TextInput(
            attrs={"class": "form-control", "autocomplete": "given-name"}
        ),
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        label="نام خانوادگی",
        widget=forms.TextInput(
            attrs={"class": "form-control", "autocomplete": "family-name"}
        ),
    )
    username = forms.CharField(
        max_length=100,
        label="نام کاربری",
        widget=forms.TextInput(
            attrs={"class": "form-control", "autocomplete": "username"}
        ),
    )
    email = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "autocomplete": "email"}
        ),
    )
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if not self.is_bound:
            self.initial.update(
                {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "email": user.email,
                }
            )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً برای حساب دیگری ثبت شده است.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"]
        if (
            User.objects.exclude(pk=self.user.pk)
            .filter(username__iexact=username)
            .exists()
        ):
            raise forms.ValidationError("این نام کاربری قبلاً انتخاب شده است.")
        return username

    def save(self):
        for field in ("first_name", "last_name", "username", "email"):
            setattr(self.user, field, self.cleaned_data[field])
        self.user.save(update_fields=("first_name", "last_name", "username", "email"))


class ProductReviewForm(forms.ModelForm):
    review = forms.CharField(widget=forms.Textarea(attrs={'placeholder': "پیام شما"}))

    class Meta:
        model = ProductReview
        fields = ['review', 'rating']