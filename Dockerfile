FROM python:3.7-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HOME /usr/src/app

WORKDIR $HOME
RUN adduser --disabled-password python && chown -R python:python $HOME

RUN apk add --no-cache --update mariadb-connector-c-dev \
 && apk add --no-cache --virtual .build mariadb-dev gcc musl-dev \
 && pip install mysqlclient gunicorn \
 && apk --purge del .build

COPY --chown=python requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=python . .

USER python
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
EXPOSE 8000

