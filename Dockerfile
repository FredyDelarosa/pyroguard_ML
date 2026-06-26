# Usar imagen oficial ligera de Python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Usuario sin privilegios
RUN adduser --disabled-password --gecos '' mluser

# Instalar dependencias del sistema espaciales (GDAL, GEOS) y para compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código y modelos
COPY . .

# Cambiar permisos de la carpeta de modelos en caso de que el worker necesite guardar algo
RUN chown -R mluser:mluser /app/models || true

# Cambiar al usuario sin privilegios
USER mluser

# Exponer el puerto interno
EXPOSE 8000

# Por defecto arranca la API, pero docker-compose puede sobreescribir este comando para arrancar Celery
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
