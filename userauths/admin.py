from django.contrib import admin
from userauths.models import User, ContactUs, Profile

class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'bio_summary']
    list_display_links = ['username']
    search_fields = ['username', 'email']

    @admin.display(description="معرفی کوتاه")
    def bio_summary(self, obj):
        return obj.bio or "—"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "bio" in form.base_fields:
            form.base_fields["bio"].label = "معرفی کوتاه"
        return form

class ContactUsAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'subject']


# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ['user', 'full_name', 'bio', 'phone']


admin.site.register(User, UserAdmin)
admin.site.register(ContactUs, ContactUsAdmin)
admin.site.register(Profile)