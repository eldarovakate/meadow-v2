from .base import *
import dj_database_url

DEBUG = config('DEBUG', default=False, cast=bool)
# Основной домен разрешён всегда; дополнительные хосты — через ALLOWED_HOSTS в .env.
# Без "*": иначе Host-заголовок запроса мог бы подставлять чужой домен в абсолютные ссылки.
ALLOWED_HOSTS = ['meadowshore.ru', 'www.meadowshore.ru'] + [
    h for h in config('ALLOWED_HOSTS', default='', cast=Csv()) if h and h != '*'
]

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

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = False
# nginx перед этим сервером передаёт proxy_set_header X-Forwarded-Proto $scheme
# (подтверждено вручную на 89.104.71.175) — без этого Django строит
# return_url для ЮKassa (request.build_absolute_uri) с http:// вместо https://.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = ['https://meadowshore.ru', 'https://www.meadowshore.ru']
WAGTAILADMIN_BASE_URL = 'https://meadowshore.ru'
SITE_URL = config('SITE_URL', default='https://meadowshore.ru')

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    # Ошибки внешних сервисов (ЮKassa, SMTP, Telegram) из website/accounts — в journald.
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
