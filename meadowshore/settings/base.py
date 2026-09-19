import os
from datetime import date
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

INSTALLED_APPS = [
    'home',
    'website',
    'accounts',

    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.contrib.settings',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',

    'modelcluster',
    'taggit',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

ROOT_URLCONF = 'meadowshore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.cart',
                'website.context_processors.favorites',
                'website.context_processors.sales_mode',
                'wagtail.contrib.settings.context_processors.settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'meadowshore.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

WAGTAIL_SITE_NAME = 'Meadow Shore'
WAGTAILADMIN_BASE_URL = 'http://localhost:8000'
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 10 * 1024 * 1024

LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/account/'

# Уведомления о новых заказах
ORDER_NOTIFICATION_EMAIL = config('ORDER_NOTIFICATION_EMAIL', default='info@meadowshore.ru')
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID', default='')

# ЮKassa
YOOKASSA_SHOP_ID = config('YOOKASSA_SHOP_ID', default='')
YOOKASSA_SECRET_KEY = config('YOOKASSA_SECRET_KEY', default='')

# Режим продаж сайта: 'preorder' (оплата не запрашивается, только сбор предзаказов)
# или 'sales' (обычный flow с оплатой через ЮKassa). Единственный источник истины —
# это backend-проверка в website.views.checkout_view, а не текст на кнопках.
SALES_MODE = config('SALES_MODE', default='sales')
SALES_OPEN_DATE = date.fromisoformat(config('SALES_OPEN_DATE', default='2026-10-01'))

# Показывать ли кнопку "Оформить заказ/предзаказ" в корзине. По умолчанию включено
# (нужно на локальной/тестовой среде, чтобы продолжать дорабатывать checkout);
# на проде временно выключается через CHECKOUT_ENABLED=False в .env.
CHECKOUT_ENABLED = config('CHECKOUT_ENABLED', default=True, cast=bool)
