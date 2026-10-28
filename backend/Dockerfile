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

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/db', timeout=2)"

# Las IPs de confianza para X-Forwarded-For se leen de FORWARDED_ALLOW_IPS
# (por defecto solo 127.0.0.1). Nunca "*": permitiría falsear la IP del
# cliente y saltarse el límite de intentos de login.
# Un solo proceso (sin --workers): el registro de WebSockets del chat está en
# memoria (ver app/realtime.py).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
