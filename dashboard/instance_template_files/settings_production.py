from pathlib import Path
from dotenv import load_dotenv
import os
import json

load_dotenv()

DEFAULT_FILE_TRANSFER_DESTINATIONS = {
    9000 : "Download as Files",
    9001 : "Download as JSON",
    9002 : "Share Folder",
    9003 : "RAPiD-e"
}

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

default_config_file_path = BASE_DIR / 'site-config.json'
config_path = os.getenv("ADDMAN_SITE_CONFIG_PATH", default_config_file_path)
db_id = "defaultid"
uid_counter = 1000

try:
    with open(config_path, "r") as file:
        data = json.load(file)

        if ("sftp_destinations" in data):
            for dest in data["sftp_destinations"]:
                index = len(DEFAULT_FILE_TRANSFER_DESTINATIONS)
                DEFAULT_FILE_TRANSFER_DESTINATIONS.update({ index: dest["name"] })

        if ("db_id" in data):
            db_id = data["db_id"]

        if ("uid_counter" in data):
            uid_counter = int(data["uid_counter"])
except FileNotFoundError:
    pass

DB_ID = os.getenv("ADDMAN_DB_ID", db_id)
UID_COUNTER = uid_counter

app_name = os.getenv('AMSYS_APP_NAME', '')
app_name = app_name.replace('/', '')

if (app_name != ''):
    FORCE_SCRIPT_NAME = f"/{app_name}"

app_url_prefix = f"{app_name}/"
STATIC_URL = app_url_prefix + 'static/'
STATIC_ROOT = BASE_DIR / "static_production"
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

LOGIN_URL = "/login"

if (app_name != ''):
    LOGIN_URL = f"/{app_name}/login"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('ADDMAN_SECRET_KEY', None)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    'addmanjojak.deflab.fi'
]


# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = True

SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Application definition

INSTALLED_APPS = [
    'myapp',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    "django_extensions",
    'rest_framework',
    'channels',
]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',  # Use Redis as the channel layer backend
        'CONFIG': {
            'hosts': [('localhost', 6379)],  # Adjust the host and port as per your Redis configuration
        },
    },
}

ASGI_APPLICATION = "3D-Repository.asgi.application"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://135.225.57.136",
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = '3D-Repository.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, '/myapp/templates/'),
            os.path.join(BASE_DIR, 'templates/'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'myapp.controller.template_variables',
            ],
        },
    },
]

WSGI_APPLICATION = '3D-Repository.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'Database/db.sqlite3'),
    }
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    # },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#  SECURE_SSL_REDIRECT = True
#  SESSION_COOKIE_SECURE = True
#  CSRF_COOKIE_SECURE = True
#  PREPEND_WWW = True
#  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# BASE_URL = "https://komati.work.gd"

CSRF_TRUSTED_ORIGINS = [
    'https://*.127.0.0.1',
    'http://*.127.0.0.1',
    'http://135.225.57.136',
    'http://addmanext.swedencentral.cloudapp.azure.com',
    'https://addmanext.swedencentral.cloudapp.azure.com',
    'http://192.168.111.10'
]

DATA_UPLOAD_MAX_MEMORY_SIZE = 1073741824
