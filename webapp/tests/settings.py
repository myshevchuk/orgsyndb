"""Settings of the application's tests: SQLite unless
ORGSYNDB_DATABASE_URL names another database."""

import os

os.environ.setdefault("ORGSYNDB_SECRET_KEY", "test-only-secret-key")
os.environ.setdefault("ORGSYNDB_ALLOWED_HOSTS", "testserver,lab.example.org")
os.environ.setdefault("ORGSYNDB_INDEX", "/nonexistent/orgsyndb/index.json")

from orgsyndb_web.settings import *  # noqa: E402,F401,F403

# Tests that freeze the clock log in outside the frozen time.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 365 * 50
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# Tests read the stylesheets' literal paths, not fingerprinted ones.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
