FROM python:3.13.15-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e

# This timestamp and the base digest must be reviewed together when updating.
ARG DEBIAN_SNAPSHOT=20260901T000000Z
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# A fixed, signed Debian snapshot prevents an unrelated apt repository update
# from silently changing the document toolchain. Signature checks stay enabled.
RUN printf '%s\n' \
      'Types: deb' \
      "URIs: https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/" \
      'Suites: bookworm bookworm-updates' \
      'Components: main' \
      'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
      'Check-Valid-Until: no' \
      '' \
      'Types: deb' \
      "URIs: https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}/" \
      'Suites: bookworm-security' \
      'Components: main' \
      'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
      'Check-Valid-Until: no' \
      > /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      fonts-dejavu-core \
      fonts-liberation2 \
      libreoffice-writer \
      poppler-utils \
      tesseract-ocr \
      tesseract-ocr-eng \
      tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

COPY skills/ksrf-complaint-cycle/configs/plugin-requirements.txt /opt/ksrf/requirements.txt
RUN python -m pip install --no-cache-dir -r /opt/ksrf/requirements.txt \
    && python -m pip check \
    && python -m pip freeze --all > /opt/ksrf/python-packages.txt \
    && dpkg-query -W > /opt/ksrf/system-packages.txt

# Build context is the generated plugin root, never a case folder or user home.
COPY skills/ /opt/ksrf/skills/
COPY environment/smoke.py /opt/ksrf/environment/smoke.py
COPY environment/soffice.py /usr/local/bin/soffice
COPY LICENSE /opt/ksrf/LICENSE
RUN chmod 0755 /usr/local/bin/soffice \
    && groupadd --gid 10001 ksrf \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin ksrf \
    && mkdir /cases \
    && chown ksrf:ksrf /cases

USER 10001:10001
WORKDIR /cases
RUN python /opt/ksrf/environment/smoke.py --expect-unprivileged

# There is deliberately no listener, EXPOSE, or background service.
ENTRYPOINT ["python", "/opt/ksrf/skills/ksrf-complaint-cycle/scripts/ksrf.py"]
CMD ["--help"]
