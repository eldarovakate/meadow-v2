import re

from django import forms


def normalize_phone(value):
    """
    Приводит телефон к виду +7XXXXXXXXXX. Принимает обычные российские варианты
    (+7 / 8 / 7 / 10 цифр с 9…, с пробелами, скобками, дефисами). Международный
    номер, начинающийся с «+» (не +7), принимается как есть: 8–15 цифр.
    Возвращает None, если номер распознать нельзя.
    """
    raw = (value or "").strip()
    digits = re.sub(r"\D", "", raw)

    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if len(digits) == 10 and digits[0] == "9" and not raw.startswith("+"):
        return "+7" + digits
    if raw.startswith("+") and not digits.startswith("7") and 8 <= len(digits) <= 15:
        return "+" + digits
    return None


class CheckoutForm(forms.Form):
    full_name = forms.CharField(label="ФИО", max_length=255)
    phone = forms.CharField(
        label="Телефон",
        max_length=20,
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
    )
    email = forms.EmailField(label="Email", required=False)
    city = forms.CharField(label="Город", max_length=100)
    street = forms.CharField(label="Улица", max_length=255)
    house = forms.CharField(label="Дом, квартира", max_length=50)
    postal_code = forms.CharField(label="Почтовый индекс", max_length=20, required=False)
    comment = forms.CharField(
        label="Комментарий к заказу",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    # Одноразовый ключ отправки формы: защищает от двойного POST (см. checkout_view).
    checkout_token = forms.CharField(widget=forms.HiddenInput, required=False, max_length=64)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not phone:
            raise forms.ValidationError("Введите номер телефона, например +7 900 123-45-67")
        return phone
