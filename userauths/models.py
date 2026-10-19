from enum import unique
from django.db import models
from django.contrib.auth.models import AbstractUser 
from django.db.models.signals import post_save


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100)
    bio = models.CharField(max_length=100)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username
    
    


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,verbose_name="کاربر")
    image = models.ImageField(upload_to="image", null=True, blank=True,verbose_name="عکس")
    full_name = models.CharField(max_length=200, null=True, blank=True,verbose_name="نام و نام خوانوادگی")
    bio = models.CharField(max_length=200, null=True, blank=True,verbose_name="بیوگرافی")
    phone = models.CharField(max_length=200, null=True, blank=True,verbose_name="موبایل")
    address = models.CharField(max_length=200, null=True, blank=True,verbose_name="آدرس")
    country = models.CharField(max_length=200, null=True, blank=True,verbose_name="کشور")
    verified = models.BooleanField(default=False, null=True, blank=True,verbose_name="تایید شده است")

    class Meta:
        verbose_name = "پروفایل ها"
        verbose_name_plural = "پروفایل"
    
    def __str__(self):
        return f"{self.user.username} - {self.full_name} - {self.bio}"


class ContactUs(models.Model):
    full_name = models.CharField(max_length=200,verbose_name="نام و نام خوانوادگی")
    email = models.CharField(max_length=200,verbose_name="ایمیل")
    phone = models.CharField(max_length=200,verbose_name="موبایل")
    subject = models.CharField(max_length=200,verbose_name="موضوع")
    message = models.TextField(verbose_name="پیام")

    class Meta:
        verbose_name = "پیام ها"
        verbose_name_plural = "تماس با ما"

    def __str__(self):
        return self.full_name

    
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

 
post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)    



