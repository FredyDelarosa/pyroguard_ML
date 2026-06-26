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
                ml_result = evaluate_risk(temp=temp, hum=hum, wind=wind, prec=prec)
                
                nivel_riesgo = ml_result["nivel_riesgo"]
                detalles = ml_result["detalles"]
                
                # 3. Generar la alerta con NLP
                directiva = generate_directive(nivel_riesgo=nivel_riesgo, temp=temp, hum=hum, viento=wind)
                
                # 4. Guardar Predicción Histórica para el Dashboard/Frontend
                nueva_prediccion = PrediccionRiesgo(
                    id_zona=zona.id_zona,
                    fecha_evaluacion=datetime.now(),
                    nivel_riesgo=nivel_riesgo,
                    resultados_json=detalles,
                    directiva_nlp=directiva
                )
                db.add(nueva_prediccion)
                
                print(f"[ALERTA {nivel_riesgo.upper()}] Predicción generada con éxito para {zona.nombre}.")
                
            else:
                print(f"[ERROR] Open-Meteo falló para {zona.nombre}: HTTP {response.status_code}")

        db.commit()
        print("Tarea 'fetch_current_weather' completada. Base de datos e Inferencias actualizadas.")

    except Exception as e:
        print(f"[ERROR CRÍTICO] Tarea Celery fallida: {str(e)}")
        db.rollback()
    finally:
        db.close()
