FROM python:3.14.2-slim-bookworm AS builder

ARG VERSION

ENV VIRTUAL_ENV=/opt/datamodel-code-generator
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

LABEL maintainer="Koudai Aono <koxudaxi@gmail.com>"

RUN python -m venv "${VIRTUAL_ENV}"
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "datamodel-code-generator[http]==${VERSION}"

FROM python:3.14.2-slim-bookworm

LABEL maintainer="Koudai Aono <koxudaxi@gmail.com>"

ENV VIRTUAL_ENV=/opt/datamodel-code-generator
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY --from=builder /opt/datamodel-code-generator /opt/datamodel-code-generator

ENTRYPOINT ["datamodel-codegen"]
