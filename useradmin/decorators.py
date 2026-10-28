from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            messages.warning(request, "برای دسترسی به این صفحه باید با حساب مدیر وارد شوید.")
            return redirect("userauths:sign-in")
        return view_func(request, *args, **kwargs)
    return wrapper
