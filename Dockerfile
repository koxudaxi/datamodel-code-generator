FROM python:3.14.2-slim-bookworm AS builder

ARG VERSION

ENV VIRTUAL_ENV=/opt/datamodel-code-generator
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

LABEL maintainer="Koudai Aono <koxudaxi@gmail.com>"

RUN test -n "${VERSION}" \
    || { echo "The VERSION build arg is required." >&2; exit 1; } \
    && python -m venv "${VIRTUAL_ENV}" \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "datamodel-code-generator[http]==${VERSION}"

FROM python:3.14.2-slim-bookworm

LABEL maintainer="Koudai Aono <koxudaxi@gmail.com>"

ENV VIRTUAL_ENV=/opt/datamodel-code-generator
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN useradd --create-home --shell /usr/sbin/nologin appuser
COPY --from=builder --chown=appuser:appuser /opt/datamodel-code-generator /opt/datamodel-code-generator
USER appuser

ENTRYPOINT ["datamodel-codegen"]
