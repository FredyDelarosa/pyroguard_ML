import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database.connection import get_db
from database.models import ZonaProtegida, PrediccionRiesgo
from api.schemas import ZonaCreate, ZonaResponse, ZonaRiesgoPublico

router = APIRouter()

@router.get("/riesgo-publico", response_model=List[ZonaRiesgoPublico])
def listar_riesgo_publico(db: Session = Depends(get_db)):
    """
    Devuelve la lista de zonas con su último nivel de riesgo,
    ideal para el portal ciudadano sin exponer datos técnicos (HU23).
    """
    zonas = db.query(ZonaProtegida).all()
    resultado = []
    
    for zona in zonas:
        ultima_pred = db.query(PrediccionRiesgo)\
            .filter(PrediccionRiesgo.id_zona == zona.id_zona)\
            .order_by(PrediccionRiesgo.fecha_evaluacion.desc())\
            .first()
            
        nivel = ultima_pred.nivel_riesgo if ultima_pred else "Desconocido"
        resultado.append(ZonaRiesgoPublico(nombre=zona.nombre, nivel_riesgo=nivel))
        
    return resultado

@router.get("/", response_model=List[ZonaResponse])
def listar_zonas(db: Session = Depends(get_db)):
    """
    Devuelve la lista de todas las Zonas Protegidas registradas en PostGIS, incluyendo su geometría GeoJSON.
    """
    resultados = db.query(
        ZonaProtegida.id_zona,
        ZonaProtegida.nombre,
        ZonaProtegida.area_hectareas,
        func.ST_AsGeoJSON(ZonaProtegida.geometria).label("geojson")
    ).all()
    
    return [
        ZonaResponse(
            id_zona=r.id_zona,
            nombre=r.nombre,
            area_hectareas=r.area_hectareas or 0.0,
            geojson=r.geojson
        ) for r in resultados
    ]

@router.post("/", response_model=ZonaResponse)
def crear_zona_protegida(zona_in: ZonaCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva zona de monitoreo recibiendo el GeoJSON dibujado por el Administrador (HU22).
    """
    # Verificar si el nombre ya existe
    existe = db.query(ZonaProtegida).filter(ZonaProtegida.nombre == zona_in.nombre).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe una zona con ese nombre.")
        
    geojson_str = json.dumps(zona_in.geojson_polygon)
    
    # 1. Creamos el objeto en la BD. Usamos ST_GeomFromGeoJSON para que PostgreSQL lo convierta a su binario espacial
    # 2. ST_Area y conversiones pueden hacerse usando SQLAlchemy o con una consulta raw.
    # Por simplicidad y eficiencia, ejecutamos la inserción usando funciones espaciales SQL.
    
    try:
        from sqlalchemy import text
        insert_query = text("""
            INSERT INTO zonas_protegidas (nombre, geometria)
            VALUES (:nombre, ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))
            RETURNING id_zona, nombre, area_hectareas;
        """)
        
        resultado = db.execute(insert_query, {
            "nombre": zona_in.nombre,
            "geojson": geojson_str
        }).fetchone()
        
        # Opcional: Actualizar el área (PostGIS ST_Area)
        update_area = text("""
            UPDATE zonas_protegidas 
            SET area_hectareas = ST_Area(geometria::geography) / 10000 
            WHERE id_zona = :id_zona
        """)
        db.execute(update_area, {"id_zona": resultado.id_zona})
        db.commit()
        
        # Devolvemos el registro recién creado
        zona_creada = db.query(ZonaProtegida).filter(ZonaProtegida.id_zona == resultado.id_zona).first()
        return zona_creada
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error espacial al guardar la zona: {str(e)}")

@router.get("/{id_zona}/clima")
def obtener_clima_zona(id_zona: str, db: Session = Depends(get_db)):
    """
    Devuelve las últimas condiciones meteorológicas registradas para una zona (HU28).
    Se expone para que el backend operativo lo consuma en su portal ciudadano.
    """
    from database.models import CondicionMeteorologica
    clima = db.query(CondicionMeteorologica)\
        .filter(CondicionMeteorologica.id_zona == id_zona)\
        .order_by(CondicionMeteorologica.fecha_hora.desc())\
        .first()
        
    if not clima:
        raise HTTPException(status_code=404, detail="No hay datos climáticos para esta zona")
        
    # Formateo simplificado (Lenguaje Coloquial para Ciudadanos)
    mensaje_riesgo = ""
    if clima.viento > 25 and clima.precipitacion == 0:
        mensaje_riesgo = "Lleva varios días sin llover y el viento está fuerte, eso aumenta el peligro."
    elif clima.temperatura > 32:
        mensaje_riesgo = "Hace mucho calor y esto seca la vegetación."
    else:
        mensaje_riesgo = "Las condiciones actuales son estables."
        
    return {
        "temperatura_actual": f"{clima.temperatura} °C",
        "humedad": f"{clima.humedad}%",
        "viento": f"{clima.viento} km/h",
        "dias_sin_lluvia": "Sin precipitaciones recientes" if clima.precipitacion == 0 else "Lluvia reciente",
        "analisis_simple": mensaje_riesgo
    }
