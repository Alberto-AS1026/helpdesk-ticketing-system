FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

# 1. Dependencias (capa cacheable)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Código
COPY app ./app

# 3. Usuario sin privilegios; el directorio de logs debe poder escribirse
RUN useradd --create-home --uid 1001 appuser \
    && mkdir -p /srv/logs \
    && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
