FROM node:lts-alpine as frontend-builder

ARG PUBLIC_URL=

WORKDIR /build
COPY web/package.json ./
COPY web/yarn.lock ./
RUN yarn
COPY web/ ./
RUN yarn build


FROM python:3.12-slim as app

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  gcc libpq-dev python3-dev 

RUN pip install pipenv

COPY api/Pipfile api/Pipfile.lock ./
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

COPY api/ .
COPY --from=frontend-builder /build/build ./static

RUN adduser --system --no-create-home --group sqlbot \
  && chown -R sqlbot:sqlbot /app
USER sqlbot:sqlbot

ENTRYPOINT [ "pipenv", "run", "uvicorn", "sqlbot.main:app" ]
CMD [ "--host", "0.0.0.0", "--port", "8000" ]
