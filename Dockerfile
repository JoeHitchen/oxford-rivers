FROM python:3.7

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN useradd django
WORKDIR /usr/src/app

RUN pip install mysqlclient gunicorn

COPY --chown=django requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=django . .

USER django
