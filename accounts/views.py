from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render

from .forms import EmailLoginForm, RegistrationForm

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect("account")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("account")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("account")

    if request.method == "POST":
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            password = form.cleaned_data["password"]
            user = None
            try:
                existing = User.objects.get(email__iexact=email)
                user = authenticate(request, username=existing.username, password=password)
            except User.DoesNotExist:
                user = None

            if user is not None:
                login(request, user)
                if not form.cleaned_data.get("remember_me"):
                    request.session.set_expiry(0)
                return redirect("account")
            messages.error(request, "Неверный email или пароль.")
    else:
        form = EmailLoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("/")


def password_reset_view(request):
    return render(request, "accounts/password_reset.html")
