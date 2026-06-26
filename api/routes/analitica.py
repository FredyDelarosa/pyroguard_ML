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
