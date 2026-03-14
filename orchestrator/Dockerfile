FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar algunos paquetes (ej: psycopg2, qdrant-client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar el caché de Docker
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el proyecto al contenedor
COPY . /app

EXPOSE 8000

# Lanzar FastAPI
CMD ["uvicorn", "orchestrator.orchestrator:app", "--host", "0.0.0.0", "--port", "8000"]
