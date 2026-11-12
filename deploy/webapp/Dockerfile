# The lab application's image: Django served by gunicorn on port 8000,
# behind the web service's Caddy, which forwards /lab/ to it. Built from
# the repository root with deploy/compose.yaml, which sets the context;
# it takes webapp/ and the site's stylesheets, site/assets/css/, from
# the checkout. Updating the application means rebuilding this image;
# the container applies pending migrations when it starts, and with
# ORGSYNDB_DEMO=true fills an empty database with the demo data. See the
# README's "Container deployment".
FROM fedora:44

RUN dnf install -y --setopt=install_weak_deps=False python3 uv \
    && dnf clean all \
    && useradd --uid 1000 --user-group --create-home orgsyndb

# The locked dependencies, without the development ones, in a virtual
# environment outside the source tree, on Fedora's Python.
ENV UV_PROJECT_ENVIRONMENT=/opt/orgsyndb/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/orgsyndb/venv/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /opt/orgsyndb/webapp
COPY webapp/pyproject.toml webapp/uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

COPY site/assets/css/ /opt/orgsyndb/site/assets/css/
COPY webapp/ /opt/orgsyndb/webapp/
# collectstatic needs settings but no database.
RUN ORGSYNDB_SECRET_KEY=collectstatic ORGSYNDB_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

USER orgsyndb
EXPOSE 8000
# Pending migrations first, then the demo data, which only an empty
# database with ORGSYNDB_DEMO=true receives, then the application.
CMD ["sh", "-c", "python manage.py migrate --noinput \
&& python manage.py demo_data --if-empty && exec gunicorn \
orgsyndb_web.wsgi --bind 0.0.0.0:8000 --workers 3 --access-logfile -"]
