# OrgSynDB container image: the build tools, Caddy, and a clone of the
# application with its fetched tools cached, so the first build needs no
# internet access. The application then follows ORGSYNDB_APP_REPO by
# itself; this image needs rebuilding only when deploy/docker/ changes.
# Build it with deploy/compose.yaml; see the README's "Container
# deployment".
FROM fedora:44

# Repositories mounted from the host under /srv/git/ belong to another
# user; safe.directory lets Git fetch from them.
RUN dnf install -y --setopt=install_weak_deps=False \
        python3 hugo weasyprint emacs-nox git-core openssh-clients caddy \
        ca-certificates tar gzip \
    && dnf clean all \
    && git config --system --add safe.directory '/srv/git/*' \
    && useradd --uid 1000 --user-group --create-home orgsyndb \
    && install -d -o orgsyndb -g orgsyndb /opt/orgsyndb /var/lib/orgsyndb

ARG APP_REPO=https://github.com/myshevchuk/orgsyndb.git
ARG APP_REF=main

USER orgsyndb
# Caddy keeps its state under these; the web service mounts a volume on
# the first, which takes its owner from the image.
# Building the demo caches ox-hugo, tomelr and Pagefind in the clone.
RUN mkdir -p /home/orgsyndb/.local/share/caddy /home/orgsyndb/.config/caddy \
    && git clone --quiet --branch "$APP_REF" "$APP_REPO" /opt/orgsyndb/app \
    && cd /opt/orgsyndb/app \
    && tools/orgsyndb -C examples/demo build \
    && tools/orgsyndb -C examples/demo clean \
    && printf '{"app_repo": "%s", "app_ref": "%s", "deploy_tree": "%s"}\n' \
        "$APP_REPO" "$APP_REF" "$(git rev-parse HEAD:deploy/docker)" \
        > /opt/orgsyndb/image.json

USER root
RUN install -m 755 /opt/orgsyndb/app/deploy/docker/orgsyndb-deploy \
        /usr/local/bin/orgsyndb-deploy \
    && install -m 644 /opt/orgsyndb/app/deploy/docker/Caddyfile \
        /etc/caddy/Caddyfile

USER orgsyndb
ENV HOME=/home/orgsyndb
WORKDIR /var/lib/orgsyndb
VOLUME /var/lib/orgsyndb
EXPOSE 8080
CMD ["orgsyndb-deploy", "run"]
