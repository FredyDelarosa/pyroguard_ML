from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from geoalchemy2 import Geometry
from .connection import Base

class ZonaProtegida(Base):
    __tablename__ = "zonas_protegidas"
    
    id_zona = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(255), unique=True, nullable=False)
    geometria = Column(Geometry('POLYGON', srid=4326), nullable=False)
    area_hectareas = Column(Float)

class CondicionMeteorologica(Base):
    __tablename__ = "condiciones_meteorologicas"
    
    id_condicion = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_zona = Column(UUID(as_uuid=True), ForeignKey("zonas_protegidas.id_zona", ondelete="CASCADE"))
    fecha_hora = Column(DateTime, nullable=False)
    temperatura = Column(Float)
    humedad = Column(Float)
    viento = Column(Float)
    precipitacion = Column(Float)
    
    zona = relationship("ZonaProtegida")

class IncidenteHistorico(Base):
    __tablename__ = "incidentes_historicos"
    
    id_incidente = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_zona = Column(UUID(as_uuid=True), ForeignKey("zonas_protegidas.id_zona", ondelete="CASCADE"))
    fecha_deteccion = Column(DateTime, nullable=False)
    fuente = Column(String(50), nullable=False)
    coordenada = Column(Geometry('POINT', srid=4326), nullable=False)
    
    zona = relationship("ZonaProtegida")

class PrediccionRiesgo(Base):
    __tablename__ = "predicciones_riesgo"
    
    id_prediccion = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_zona = Column(UUID(as_uuid=True), ForeignKey("zonas_protegidas.id_zona", ondelete="SET NULL"), nullable=True)
    fecha_evaluacion = Column(DateTime, nullable=False, default=func.now())
    nivel_riesgo = Column(String(50), nullable=False)
    resultados_json = Column(JSONB)
    directiva_nlp = Column(Text)
    
    zona = relationship("ZonaProtegida")
