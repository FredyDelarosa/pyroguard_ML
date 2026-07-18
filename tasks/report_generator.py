import requests
import json
from celery_app import app
from database.connection import SessionLocal
from database.models import ZonaProtegida, PrediccionRiesgo, CondicionMeteorologica
from services.rules_engine import ReportRulesEngine
from services.llm_service import ReportGeneratorLLM

@app.task(bind=True, max_retries=3)
def generate_and_send_report(self, id_zona: str, webhook_url: str):
    """
    Tarea asíncrona de Celery que genera el reporte con el LLM y lo envía de vuelta al Backend.
    """
    print(f"[{self.request.id}] Iniciando generación de reporte para zona: {id_zona}")
    
    db = SessionLocal()
    try:
        # 1. Obtener la información de la zona y la última predicción
        zona = db.query(ZonaProtegida).filter(ZonaProtegida.id_zona == id_zona).first()
        if not zona:
            print(f"[{self.request.id}] Error: Zona no encontrada.")
            return {"status": "error", "detail": "Zona no encontrada"}
            
        prediccion = db.query(PrediccionRiesgo).filter(PrediccionRiesgo.id_zona == id_zona).order_by(PrediccionRiesgo.fecha_evaluacion.desc()).first()
        
        if not prediccion:
            print(f"[{self.request.id}] Error: No hay datos de predicción para esta zona.")
            return {"status": "error", "detail": "No hay predicciones recientes para esta zona"}

        # Extraer el clima real almacenado
        condicion = db.query(CondicionMeteorologica).filter(CondicionMeteorologica.id_zona == id_zona).order_by(CondicionMeteorologica.fecha_hora.desc()).first()
        temp_real = condicion.temperatura if condicion else 38.5
        hum_real = condicion.humedad if condicion else 12.0
        viento_real = condicion.viento if condicion else 45.0

        # 2. Reconstruir el ml_payload
        ml_payload = {
            "nivel_riesgo": prediccion.nivel_riesgo,
            "zona_nombre": zona.nombre,
            "detalles": prediccion.resultados_json or {},
            "meteo_data": {
                "temp": temp_real,
                "hum": hum_real,
                "wind": viento_real
            }
        }
        
        # 3. Construir el contexto RAG
        print(f"[{self.request.id}] Armando paquete de contexto RAG...")
        engine = ReportRulesEngine()
        contexto_final = engine.build_system_context(ml_payload)
        
        # 4. Inferencia LLM
        print(f"[{self.request.id}] Pasando contexto a Llama 3 para inferencia...")
        llm = ReportGeneratorLLM()
        reporte_json = llm.generate_report_json(contexto_final)
        
        # 5. Enviar el JSON de regreso al Webhook
        print(f"[{self.request.id}] Reporte generado. Enviando a webhook: {webhook_url}")
        
        payload_webhook = {
            "id_zona": id_zona,
            "task_id": self.request.id,
            "reporte_json": reporte_json
        }
        
        respuesta = requests.post(webhook_url, json=payload_webhook, timeout=10)
        
        if respuesta.status_code in (200, 201):
            print(f"[{self.request.id}] ¡Entregado con éxito al backend operativo!")
            return {"status": "success", "task_id": self.request.id}
        else:
            print(f"[{self.request.id}] El backend operativo rechazó el webhook. Codigo: {respuesta.status_code}")
            return {"status": "error", "detail": f"Webhook rechazado: {respuesta.status_code}"}
            
    except Exception as e:
        print(f"[{self.request.id}] Fallo crítico en la tarea: {str(e)}")
        # Reintentar si hubo un fallo transitorio
        self.retry(exc=e, countdown=60)
        
    finally:
        db.close()
