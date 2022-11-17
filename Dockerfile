FROM python:3.11.0-alpine3.16 as builder

LABEL maintainer="Koudai Aono <koxudaxi@gmail.com>"

RUN apk add --no-cache gcc musl-dev

ARG VERSION

RUN pip install "datamodel-code-generator[http]==$VERSION"

ENTRYPOINT ["datamodel-codegen"]
