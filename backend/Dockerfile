# backend/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# собрать статику во время сборки

RUN python manage.py collectstatic --noinput

CMD ["sh","-c","python manage.py migrate && gunicorn proj.wsgi:application -b 0.0.0.0:8000"]
