"""Django settings of the OrgSynDB lab application.

The environment decides the secret key, debug, the host names, the
database and the path of the collection index; see
``orgsyndb_web.config.settings_from``.
"""

import os

from django.utils.translation import gettext_lazy as _

from orgsyndb_web.config import WEBAPP, settings_from

globals().update(settings_from(os.environ))

INSTALLED_APPS = [
    "orgsyndb_web",
    "accounts",
    "tasks",
    "inventory",
    "planning",
    "demo",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simple_history",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "orgsyndb_web.middleware.IndexLanguageMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "orgsyndb_web.urls"
WSGI_APPLICATION = "orgsyndb_web.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "orgsyndb_web.context_processors.shell",
            ],
        },
    },
]

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation."
             "UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation."
             "NumericPasswordValidator"},
]
LOGIN_URL = "/lab/accounts/login/"
LOGIN_REDIRECT_URL = "/lab/tasks/"
LOGOUT_REDIRECT_URL = "/lab/tasks/"

# Requests reach the application through Caddy, which sets the header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# The language is the collection index's; IndexLanguageMiddleware
# activates it for each request.
LANGUAGE_CODE = "de"
LANGUAGES = [("de", _("German")), ("en", _("English"))]
USE_I18N = True
FORMAT_MODULE_PATH = ["orgsyndb_web.formats"]
TIME_ZONE = "Europe/Berlin"
USE_TZ = True

STATIC_URL = "/lab/static/"
STATIC_ROOT = WEBAPP / "staticfiles"
# The site's own stylesheets, from the same checkout, under site/.
STATICFILES_DIRS = [("site", WEBAPP.parent / "site" / "assets" / "css")]
# Files keep their names, so pages link the stylesheets by them.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
