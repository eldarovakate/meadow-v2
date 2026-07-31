from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    patronymic = models.CharField(max_length=150, blank=True, verbose_name="Отчество")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    personal_data_consent = models.BooleanField(default=False, verbose_name="Согласие на обработку персональных данных")
    consent_given_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата согласия")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return self.user.email
