from django import forms

from core.models import Product
from core.upload_forms import ProductImageFormField


class AddProductForm(forms.ModelForm):
    approval = forms.BooleanField(
        required=True,
        label="اطلاعات و تطبیق تصاویر را بررسی کرده‌ام و ثبت را تأیید می‌کنم.",
    )
    title = forms.CharField(
        label="عنوان محصول",
        widget=forms.TextInput(
            attrs={"placeholder": "عنوان محصول", "class": "form-control"}
        ),
    )
    description = forms.CharField(
        label="توضیحات",
        required=True,
        widget=forms.Textarea(
            attrs={
                "placeholder": "معرفی کوتاه و توضیحات کامل را فقط بر اساس اطلاعات تأییدشده بنویسید.",
                "class": "form-control",
                "rows": 5,
            }
        ),
    )
    image = ProductImageFormField(
        required=False,
        label="تصویر اصلی",
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/jpeg,image/png,image/webp",
            }
        ),
    )
    sale_price = forms.DecimalField(
        required=False,
        initial=0,
        label="قیمت تخفیف",
        widget=forms.NumberInput(
            attrs={
                "placeholder": "قیمت پس از تخفیف",
                "class": "form-control",
                "min": 0,
            }
        ),
    )
    mfd = forms.DateTimeField(
        required=False,
        label="تاریخ ساخت",
        widget=forms.DateTimeInput(
            attrs={"placeholder": "تاریخ ساخت", "class": "form-control"}
        ),
    )

    class Meta:
        model = Product
        fields = [
            "title",
            "image",
            "description",
            "price",
            "price_pending_confirmation",
            "sale_price",
            "is_sale",
            "specifications",
            "type",
            "stock_count",
            "life",
            "mfd",
            "tags",
            "digital",
            "category",
            "subcategory",
            "product_status",
            "status",
            "in_stock",
            "featured",
        ]
        widgets = {
            "price": forms.NumberInput(
                attrs={
                    "placeholder": "قیمت فروش",
                    "class": "form-control",
                    "min": 0,
                    "step": 1,
                }
            ),
            "price_pending_confirmation": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "sale_price": forms.NumberInput(
                attrs={
                    "placeholder": "قیمت پس از تخفیف",
                    "class": "form-control",
                    "min": 0,
                }
            ),
            "specifications": forms.Textarea(
                attrs={
                    "placeholder": "مشخصات محصول",
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "type": forms.TextInput(
                attrs={"placeholder": "نوع محصول", "class": "form-control"}
            ),
            "stock_count": forms.NumberInput(
                attrs={"placeholder": "تعداد موجودی", "class": "form-control", "min": 0}
            ),
            "life": forms.TextInput(
                attrs={
                    "placeholder": "مدت گارانتی یا عمر محصول",
                    "class": "form-control",
                }
            ),
            "tags": forms.TextInput(
                attrs={"placeholder": "برچسب‌ها را با ویرگول جدا کنید", "class": "form-control"}
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "subcategory": forms.Select(attrs={"class": "form-select"}),
            "product_status": forms.Select(attrs={"class": "form-select"}),
            "is_sale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "status": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "in_stock": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "digital": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price"].required = False
        if self.instance.pk:
            self.fields.pop("approval")
            self.fields["description"].required = False
            self.fields["price"].widget.attrs["min"] = 0
        else:
            self.fields["description"].required = True
            self.fields["stock_count"].required = True
            self.fields["category"].required = True
            self.fields["tags"].required = True
            self.fields["price"].initial = None
            self.fields["stock_count"].initial = ""
        self.fields["price"].help_text = (
            "قیمت واقعی را وارد کنید؛ در صورت نامشخص بودن، گزینهٔ تأیید قیمت را فعال و وضعیت را روی پیش‌نویس بگذارید."
        )

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        duplicates = Product.objects.filter(title__iexact=title)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(
                "محصولی با این عنوان از قبل ثبت شده است؛ عنوان یا مشخصات محصول را دقیق‌تر کنید."
            )
        return title

    def clean_stock_count(self):
        stock_count = self.cleaned_data.get("stock_count")
        if stock_count in (None, ""):
            return stock_count
        if not stock_count.isdecimal():
            raise forms.ValidationError("موجودی باید عدد صحیح نامنفی باشد.")
        return stock_count

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get("price")
        sale_price = cleaned_data.get("sale_price")
        is_sale = cleaned_data.get("is_sale")
        price_pending_confirmation = cleaned_data.get("price_pending_confirmation")
        product_status = cleaned_data.get("product_status")

        if sale_price is None:
            cleaned_data["sale_price"] = sale_price = 0
        if price is None or price == 0:
            if not price_pending_confirmation:
                self.add_error(
                    "price",
                    "قیمت واقعی و مثبت لازم است؛ برای محصول بدون قیمت، تأیید قیمت را فعال کنید.",
                )
            elif product_status != "draft":
                self.add_error(
                    "product_status",
                    "تا زمان تأیید قیمت، وضعیت محصول باید پیش‌نویس باشد.",
                )
            else:
                cleaned_data["price"] = 0
            if is_sale:
                self.add_error(
                    "is_sale",
                    "برای محصولی که قیمت آن تأیید نشده، تخفیف ثبت نکنید.",
                )
        elif price < 0:
            self.add_error("price", "قیمت نمی‌تواند منفی باشد.")
        else:
            cleaned_data["price_pending_confirmation"] = False
        if sale_price is not None and sale_price < 0:
            self.add_error("sale_price", "قیمت تخفیف نمی‌تواند منفی باشد.")
        if is_sale and price is not None and sale_price is not None and sale_price >= price:
            self.add_error("sale_price", "قیمت با تخفیف باید کمتر از قیمت اصلی باشد.")
        return cleaned_data
