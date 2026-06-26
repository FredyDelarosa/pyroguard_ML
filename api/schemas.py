from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# Esquema para recibir datos del clima (Input del cliente)
class PredictionRequest(BaseModel):
    temperatura: float = Field(..., description="Temperatura máxima en °C", example=35.5)
    humedad: float = Field(..., description="Humedad relativa media en %", example=30.0)
    viento: float = Field(..., description="Velocidad del viento máxima en km/h", example=15.0)
    precipitacion: float = Field(..., description="Precipitación acumulada en mm", example=0.0)
    id_zona: Optional[UUID] = Field(None, description="UUID de la zona protegida (opcional)")

# Esquema para responder con el resultado de la inferencia (Output para el cliente)
class PredictionResponse(BaseModel):
    id_prediccion: UUID
    id_zona: Optional[UUID] = None
    nivel_riesgo: str = Field(..., description="Bajo, Medio, Alto, o Crítico")
    detalles_modelos: Dict[str, Any] = Field(..., description="Resultados crudos de KMeans e Isolation Forest")
    directiva_accion: str = Field(..., description="Texto generado por LangChain con la recomendación de mitigación")
    fecha_evaluacion: datetime

    model_config = ConfigDict(from_attributes=True)

class ZonaCreate(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=255)
    geojson_polygon: Dict[str, Any] = Field(..., description="Diccionario GeoJSON tipo Polygon o MultiPolygon")

# Esquema para devolver información de las zonas
class ZonaResponse(BaseModel):
    id_zona: UUID
    nombre: str
    area_hectareas: float
    geojson: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ZonaRiesgoPublico(BaseModel):
    nombre: str
    nivel_riesgo: str

    model_config = ConfigDict(from_attributes=True)
