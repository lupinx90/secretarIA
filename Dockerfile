FROM python:3.11-slim

# 1. Instalar herramientas del sistema (ping)
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Instalar requests mediante pip
RUN pip install --no-cache-dir requests

# 3. Copiar el código del script
COPY main.py .
COPY db.py .

CMD ["python", "-u", "main.py"]