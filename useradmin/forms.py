from django import forms

from core.models import Product
from core.upload_forms import ProductImageFormField


class AddProductForm(forms.ModelForm):
    approval = forms.BooleanField(
        required=True,
        label="اطلاعات، قیمت و تطبیق تصاویر را بررسی کرده‌ام و ثبت را تأیید می‌کنم.",
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
                    "min": 1,
                    "step": 1,
                }
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
            "قیمت واقعی و تأییدشده را وارد کنید؛ قیمت نامشخص را حدس نزنید."
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

        if sale_price is None:
            cleaned_data["sale_price"] = sale_price = 0
        if price is not None and price < 0:
            self.add_error("price", "قیمت نمی‌تواند منفی باشد.")
        elif price == 0 and not self.instance.pk:
            self.add_error("price", "برای ثبت محصول، قیمت واقعی و مثبت لازم است.")
        if sale_price is not None and sale_price < 0:
            self.add_error("sale_price", "قیمت تخفیف نمی‌تواند منفی باشد.")
        if is_sale and price is not None and sale_price is not None and sale_price >= price:
            self.add_error("sale_price", "قیمت با تخفیف باید کمتر از قیمت اصلی باشد.")
        return cleaned_data
