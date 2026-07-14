from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from database.connection import get_db
from database.models import IncidenteHistorico, PrediccionRiesgo, ZonaProtegida
from services.threshold_manager import load_thresholds, save_thresholds

router = APIRouter()

# ==============================================================
# HU15: Patrones históricos de incendios (Incidentes de Conafor)
# ==============================================================
@router.get("/incidentes-historicos")
def obtener_incidentes_historicos(limit: int = 1000, db: Session = Depends(get_db)):
    """
    Devuelve los incidentes históricos registrados para cruzar en el mapa.
    Nota: Transforma la geometría PostGIS a texto para que el frontend la lea.
    """
    resultados = db.query(
        IncidenteHistorico.id_incidente,
        IncidenteHistorico.fecha_deteccion,
        IncidenteHistorico.fuente,
        func.ST_AsText(IncidenteHistorico.coordenada).label("coordenada_wkt"),
        ZonaProtegida.nombre.label("zona_nombre")
    ).join(ZonaProtegida, IncidenteHistorico.id_zona == ZonaProtegida.id_zona).limit(limit).all()
    
    return [
        {
            "id": r.id_incidente,
            "fecha": r.fecha_deteccion,
            "fuente": r.fuente,
            "zona": r.zona_nombre,
            "coordenada_wkt": r.coordenada_wkt
        } for r in resultados
    ]

# ==============================================================
# HU16: Ajuste de umbrales de clasificación de riesgo
# ==============================================================
from pydantic import BaseModel

class CondicionUmbral(BaseModel):
    temp: float
    hum: float

class UmbralesConfig(BaseModel):
    critico: CondicionUmbral
    medio: CondicionUmbral

@router.get("/configuracion-umbrales", response_model=UmbralesConfig)
def ver_umbrales():
    return load_thresholds()

@router.put("/configuracion-umbrales")
def actualizar_umbrales(umbrales: UmbralesConfig):
    """
    Permite a los Analistas ajustar en caliente los pesos de temperatura y humedad.
    """
    umbrales_dict = umbrales.model_dump()
    save_thresholds(umbrales_dict)
    return {"status": "success", "umbrales_actuales": umbrales_dict}

# ==============================================================
# HU19: Análisis de estacionalidad del riesgo (Histórico Real)
# ==============================================================
@router.get("/estacionalidad")
def estacionalidad_riesgo(db: Session = Depends(get_db)):
    """
    Genera un mapa de calor mensual de riesgo histórico (agrupado por Zona y Mes)
    basado en los incidentes reales (incendios) de la última década.
    """
    resultados = db.query(
        ZonaProtegida.nombre,
        func.extract('month', IncidenteHistorico.fecha_deteccion).label('mes'),
        func.count(IncidenteHistorico.id_incidente).label('total_incidentes')
    ).join(
        ZonaProtegida, IncidenteHistorico.id_zona == ZonaProtegida.id_zona
    ).group_by(
        ZonaProtegida.nombre, 'mes'
    ).order_by(
        ZonaProtegida.nombre, 'mes'
    ).all()
    
    # Formatear respuesta
    estacionalidad = {}
    for r in resultados:
        zona = r.nombre
        mes = int(r.mes)
        if zona not in estacionalidad:
            estacionalidad[zona] = {}
        estacionalidad[zona][mes] = r.total_incidentes
        
    return estacionalidad

# ==============================================================
# HU: Visualización de Series de Tiempo para Frontend
# ==============================================================
from datetime import datetime, timedelta

@router.get("/serie-tiempo/{id_zona}")
def obtener_serie_tiempo(id_zona: str, dias: int = 7, db: Session = Depends(get_db)):
    """
    Devuelve las series de tiempo (clima y riesgo) de los últimos N días para una zona específica.
    Ideal para graficar en el Frontend (Recharts, Chart.js, etc).
    """
    from database.models import CondicionMeteorologica
    
    fecha_limite = datetime.utcnow() - timedelta(days=dias)
    
    # 1. Obtener serie de clima
    clima = db.query(CondicionMeteorologica)\
        .filter(CondicionMeteorologica.id_zona == id_zona)\
        .filter(CondicionMeteorologica.fecha_hora >= fecha_limite)\
        .order_by(CondicionMeteorologica.fecha_hora.asc())\
        .all()
        
    serie_clima = [
        {
            "fecha": c.fecha_hora,
            "temperatura": c.temperatura,
            "humedad": c.humedad,
            "viento": c.viento,
            "precipitacion": c.precipitacion
        } for c in clima
    ]
    
    # 2. Obtener serie de predicciones de riesgo
    predicciones = db.query(PrediccionRiesgo)\
        .filter(PrediccionRiesgo.id_zona == id_zona)\
        .filter(PrediccionRiesgo.fecha_evaluacion >= fecha_limite)\
        .order_by(PrediccionRiesgo.fecha_evaluacion.asc())\
        .all()
        
    serie_riesgo = [
        {
            "fecha": p.fecha_evaluacion,
            "nivel_riesgo": p.nivel_riesgo,
            "anomalia": p.resultados_json.get("isolation_forest_anomaly", 1) if p.resultados_json else 1,
            "anomaly_score": p.resultados_json.get("anomaly_score", 0) if p.resultados_json else 0
        } for p in predicciones
    ]
    
    return {
        "id_zona": id_zona,
        "dias_analizados": dias,
        "clima": serie_clima,
        "predicciones": serie_riesgo
    }
