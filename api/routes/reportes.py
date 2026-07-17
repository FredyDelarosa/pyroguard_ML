from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any

from tasks.report_generator import generate_and_send_report

router = APIRouter()

class ReporteRequest(BaseModel):
    id_zona: str
    webhook_url: str

@router.post("/generar")
def solicitar_reporte_asincrono(request: ReporteRequest):
    """
    Recibe la solicitud del Backend Operativo, despacha la tarea pesada a Celery,
    y responde inmediatamente para evitar que la petición HTTP se congele (Timeout).
    """
    
    # Lanzamos la tarea a la cola de Celery
    task = generate_and_send_report.delay(request.id_zona, request.webhook_url)
    
    # Respondemos inmediatamente
    return {
        "status": "procesando",
        "mensaje": "La tarea ha sido encolada con éxito. El LLM está trabajando.",
        "task_id": task.id
    }
