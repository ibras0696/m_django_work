FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir aiogram fastapi uvicorn[standard] httpx python-dotenv

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]