FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --system --no-create-home --uid 10001 api
USER api

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", \
     "--ssl-certfile", "/certs/public.crt", "--ssl-keyfile", "/certs/private.key"]
