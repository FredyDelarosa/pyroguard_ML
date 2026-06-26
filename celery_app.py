import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

REDIS_URL = os.getenv("REDIS_URL", "redis://fredy:125645@localhost:6379/0")

# Inicializar aplicación Celery
app = Celery(
    "pyroguard_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.weather_fetcher"]
)

# Configuración adicional de Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Mexico_City",
    enable_utc=False,
)

# Configurar el programador automático (Celery Beat)
app.conf.beat_schedule = {
    "fetch-weather-every-hour": {
        "task": "tasks.weather_fetcher.fetch_current_weather",
        # En producción podrías ejecutarlo cada hora (minute=0), 
        # pero aquí lo dejaremos programado para las 06:00 AM todos los días.
        "schedule": crontab(hour=6, minute=0),
    }
}
