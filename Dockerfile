FROM python:3.7

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app
RUN useradd django && chown -R django:django /usr/src/app

RUN pip install mysqlclient gunicorn

COPY --chown=django requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=django . .

USER django
