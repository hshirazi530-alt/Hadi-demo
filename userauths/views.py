from django.shortcuts import redirect, render
from userauths.forms import UserRegisterForm, ProfileForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from userauths.models import Profile, User
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


# User = settings.AUTH_USER_MODEL

def _safe_next_url(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("core:index")


def register_view(request):
    
    if request.method == "POST":
        form = UserRegisterForm(request.POST or None)
        if form.is_valid():
            new_user = form.save()
            username = form.cleaned_data.get("username" )
            messages.success(request, f"سلام {username}, حساب شما با موفقیت ایجاد شد.")
            new_user = authenticate(username=form.cleaned_data['email'],
                                    password=form.cleaned_data['password1']
            )
            login(request, new_user)

            return redirect(_safe_next_url(request))
    else:
        form = UserRegisterForm()


    context = {
        'form': form,
        'next_url': request.POST.get("next") or request.GET.get("next", ""),
    }
    return render(request, "userauths/sign-up.html", context)


def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, f"سلام شما قبلا وارد شده اید.")
        return redirect(_safe_next_url(request))
    
    if request.method == "POST":
        email = request.POST.get("email") # peanuts@gmail.com
        password = request.POST.get("password") # getmepeanuts

        try:
            user = User.objects.get(email=email)
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "شما وارد شده اید.")
                return redirect(_safe_next_url(request))
            else:
                messages.warning(request, "کاربر وجود ندارد، یک حساب کاربری ایجاد کنید.")
    
        except:
            messages.warning(request, f"کاربر با {email} وجود ندارد")
        

    
    return render(request, "userauths/sign-in.html", {
        "next_url": request.POST.get("next") or request.GET.get("next", ""),
    })

        

def logout_view(request):

    logout(request)
    messages.success(request, "شما از سیستم خارج شدید.")
    return redirect("userauths:sign-in")


@login_required
def profile_update(request):
    profile = Profile.objects.get(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.user = request.user
            new_form.save()
            messages.success(request, "نمایه با موفقیت به روز شد.")
            return redirect("core:dashboard")
    else:
        form = ProfileForm(instance=profile)

    context = {
        "form": form,
        "profile": profile,
    }

    return render(request, "userauths/profile-edit.html", context)
