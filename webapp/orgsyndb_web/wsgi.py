"""The WSGI application gunicorn serves."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orgsyndb_web.settings")

application = get_wsgi_application()
