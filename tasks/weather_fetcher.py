import requests
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

# Importar la app de Celery y la BD
from celery_app import app
from database.connection import SessionLocal
from database.models import ZonaProtegida, CondicionMeteorologica, PrediccionRiesgo

# Importar nuestros servicios de IA
from services.ml_service import evaluate_risk
from services.nlp_service import generate_directive
import os

@app.task
def fetch_current_weather():

    db: Session = SessionLocal()
    try:
        zonas = db.query(ZonaProtegida).all()
        if not zonas:
            print("No hay zonas protegidas registradas en la base de datos.")
            return

        for zona in zonas:
            centroid_query = db.query(
                func.ST_Y(func.ST_Centroid(ZonaProtegida.geometria)).label('lat'),
                func.ST_X(func.ST_Centroid(ZonaProtegida.geometria)).label('lon')
            ).filter(ZonaProtegida.id_zona == zona.id_zona).first()

            if not centroid_query:
                print(f"No se pudo calcular el centroide para {zona.nombre}")
                continue
                
            lat, lon = centroid_query.lat, centroid_query.lon

            # Llamar a Open-Meteo
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation"],
                "timezone": "America/Mexico_City"
            }

            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                temp = data['current']['temperature_2m']
                hum = data['current']['relative_humidity_2m']
                wind = data['current']['wind_speed_10m']
                prec = data['current']['precipitation']
                
                # 1. Guardar Clima Diario
                nueva_condicion = CondicionMeteorologica(
                    id_zona=zona.id_zona,
                    fecha_hora=datetime.now(),
                    temperatura=temp,
                    humedad=hum,
                    viento=wind,
                    precipitacion=prec
                )
                db.add(nueva_condicion)
                
                # 2. DISPARAR LA INTELIGENCIA ARTIFICIAL AUTOMÁTICAMENTE
                print(f"Evaluando Riesgo con IA para {zona.nombre}...")
                
                # Extraemos las estadísticas relativas (Z-Score) de esta zona
                stats = {
                    'temp_mean': zona.temp_mean, 'temp_std': zona.temp_std,
                    'hum_mean': zona.hum_mean, 'hum_std': zona.hum_std,
                    'viento_mean': zona.viento_mean, 'viento_std': zona.viento_std,
                    'prec_mean': zona.prec_mean, 'prec_std': zona.prec_std
                }
                
                ml_result = evaluate_risk(temp=temp, hum=hum, wind=wind, prec=prec, stats=stats)
                
                nivel_riesgo = ml_result["nivel_riesgo"]
                detalles = ml_result["detalles"]
                
                # 3. Generar la alerta con NLP
                directiva = generate_directive(nivel_riesgo=nivel_riesgo, temp=temp, hum=hum, viento=wind)
                
                # Obtener predicción anterior para comparar criticidad
                prediccion_anterior = db.query(PrediccionRiesgo).filter(
                    PrediccionRiesgo.id_zona == zona.id_zona
                ).order_by(PrediccionRiesgo.fecha_evaluacion.desc()).first()
                
                # 4. Guardar Predicción Histórica para el Dashboard/Frontend
                nueva_prediccion = PrediccionRiesgo(
                    id_zona=zona.id_zona,
                    fecha_evaluacion=datetime.now(),
                    nivel_riesgo=nivel_riesgo,
                    resultados_json=detalles,
                    directiva_nlp=directiva
                )
                db.add(nueva_prediccion)
                
                # 5. Notificar Webhook si aumentó el riesgo a Alto o Crítico
                niveles = {"Bajo": 1, "Medio": 2, "Alto": 3, "Crítico": 4}
                nivel_actual_val = niveles.get(nivel_riesgo, 0)
                nivel_anterior_val = niveles.get(prediccion_anterior.nivel_riesgo if prediccion_anterior else "Bajo", 0)
                
                if nivel_actual_val > nivel_anterior_val and nivel_actual_val >= 3:
                    print(f"⚠️ Aumento de criticidad detectado en {zona.nombre}. Notificando al Backend Operativo...")
                    backend_url = os.getenv("OPERATIONAL_BACKEND_URL", "http://pyroguard.inode.cloud:8001")
                    api_key = os.getenv("API_KEY", "test_api_key_123")
                    try:
                        requests.post(
                            f"{backend_url}/api/v1/notificaciones/alertas-criticidad",
                            headers={"X-API-KEY": api_key},
                            json={
                                "id_zona": str(zona.id_zona),
                                "nivel_riesgo": nivel_riesgo,
                                "mensaje": f"La zona {zona.nombre} ha subido a riesgo {nivel_riesgo.upper()}. {directiva}"
                            },
                            timeout=5
                        )
                    except Exception as req_e:
                        print(f"Error notificando al webhook: {req_e}")
                
                print(f"[ALERTA {nivel_riesgo.upper()}] Predicción generada con éxito para {zona.nombre}.")
                
            else:
                print(f"[ERROR] Open-Meteo falló para {zona.nombre}: HTTP {response.status_code}")
                
            # Pausa de 2 segundos para evitar bloqueo de Open-Meteo (Error 503/429)
            import time
            time.sleep(2)

        db.commit()
        print("Tarea 'fetch_current_weather' completada. Base de datos e Inferencias actualizadas.")

    except Exception as e:
        print(f"[ERROR CRÍTICO] Tarea Celery fallida: {str(e)}")
        db.rollback()
    finally:
        db.close()
