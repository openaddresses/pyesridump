FROM python:3.12-alpine3.19 as builder

RUN apk upgrade --update-cache && apk add --no-cache \
    build-base \
    musl-dev \
    libffi-dev \
    python3-dev \
    openssl-dev

COPY pyproject.toml poetry.lock ./
COPY esridump /esridump
RUN pip install poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-cache

FROM python:3.12-alpine3.19 as deploy

ENV LANG C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=builder /.venv ./.venv
ENV PATH="${APP_HOME}/.venv/bin:$PATH"
COPY esridump ./esridump
ENTRYPOINT ["esri2geojson"]
