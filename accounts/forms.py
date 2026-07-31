from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import Profile

User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Email", required=True)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=True)
    first_name = forms.CharField(label="Имя", max_length=150, required=True)
    patronymic = forms.CharField(label="Отчество", max_length=150, required=False)
    phone = forms.CharField(
        label="Телефон",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
    )
    personal_data_consent = forms.BooleanField(
        label="Я согласен(-на) на обработку персональных данных и принимаю условия Пользовательского соглашения",
        required=True,
    )

    field_order = [
        "email", "last_name", "first_name", "patronymic", "phone",
        "password1", "password2", "personal_data_consent",
    ]

    class Meta:
        model = User
        fields = ["email", "last_name", "first_name", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                patronymic=self.cleaned_data.get("patronymic", ""),
                phone=self.cleaned_data["phone"],
                personal_data_consent=True,
                consent_given_at=timezone.now(),
            )
        return user


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    remember_me = forms.BooleanField(label="Запомнить меня", required=False)


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Email")
