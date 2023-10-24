FROM python:3.12.0-alpine3.17 as builder

LABEL maintainer="Koudai Aono <koxudaxi@gmail.com>"

RUN apk add --no-cache gcc musl-dev

ARG VERSION

RUN pip install "datamodel-code-generator[http]==$VERSION"

ENTRYPOINT ["datamodel-codegen"]
