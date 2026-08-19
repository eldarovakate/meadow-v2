from django import forms


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
