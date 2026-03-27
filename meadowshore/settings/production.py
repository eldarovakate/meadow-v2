from .base import *
import dj_database_url

DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
ALLOWED_HOSTS = ["*"]

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
    )
}

MIDDLEWARE = ['whitenoise.middleware.WhiteNoiseMiddleware'] + MIDDLEWARE
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
CSRF_TRUSTED_ORIGINS = ['https://meadowshore.ru', 'http://meadowshore.ru', 'http://194.67.101.156:8000']
WAGTAILADMIN_BASE_URL = 'https://meadowshore.ru'

# Email (SMTP через рег.ру)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.hosting.reg.ru')
EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='info@meadowshore.ru')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Куда приходят заявки с формы контактов
WAGTAILFORMS_HELP_TEXT = ''
