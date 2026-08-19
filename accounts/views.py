from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode

from .forms import EmailLoginForm, PasswordResetRequestForm, RegistrationForm

User = get_user_model()


def _safe_next_url(request, next_url):
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return None


def register_view(request):
    next_url = _safe_next_url(request, request.GET.get("next") or request.POST.get("next"))

    if request.user.is_authenticated:
        return redirect(next_url or "account")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(next_url or "account")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form, "next": next_url or ""})


def login_view(request):
    next_url = _safe_next_url(request, request.GET.get("next") or request.POST.get("next"))

    if request.user.is_authenticated:
        return redirect(next_url or "account")

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
                return redirect(next_url or "account")
            messages.error(request, "Неверный email или пароль.")
    else:
        form = EmailLoginForm()

    return render(request, "accounts/login.html", {"form": form, "next": next_url or ""})


def logout_view(request):
    logout(request)
    return redirect("/")


def password_reset_view(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            users = User.objects.filter(email__iexact=email, is_active=True)
            for user in users:
                if not user.has_usable_password():
                    continue
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    reverse("password_reset_confirm", args=[uidb64, token])
                )
                send_mail(
                    subject="Восстановление пароля — Meadow Shore",
                    message=(
                        "Здравствуйте!\n\n"
                        "Вы запросили восстановление пароля на сайте Meadow Shore.\n"
                        "Перейдите по ссылке, чтобы задать новый пароль:\n"
                        f"{reset_url}\n\n"
                        "Ссылка действительна в течение ограниченного времени. "
                        "Если вы не запрашивали восстановление пароля — просто проигнорируйте это письмо."
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                )
            return render(request, "accounts/password_reset.html", {"form": PasswordResetRequestForm(), "sent": True})
    else:
        form = PasswordResetRequestForm()

    return render(request, "accounts/password_reset.html", {"form": form})


def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    token_valid = user is not None and default_token_generator.check_token(user, token)

    if not token_valid:
        return render(request, "accounts/password_reset_confirm.html", {"valid": False})

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Пароль успешно изменён. Теперь можно войти.")
            return redirect("login")
    else:
        form = SetPasswordForm(user)

    return render(request, "accounts/password_reset_confirm.html", {"form": form, "valid": True})
