from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# Importes absolutos basados en que la raíz de ejecución será la carpeta ML
from database.connection import get_db
from database.models import PrediccionRiesgo, ZonaProtegida
from api.schemas import PredictionRequest, PredictionResponse
from services.ml_service import evaluate_risk
from services.nlp_service import generate_directive

router = APIRouter()

@router.post("/", response_model=PredictionResponse)
def create_prediction(request: PredictionRequest, db: Session = Depends(get_db)):

    # 1. Validar si la zona existe (si el usuario mandó un id_zona)
    if request.id_zona:
        zona = db.query(ZonaProtegida).filter(ZonaProtegida.id_zona == request.id_zona).first()
        if not zona:
            raise HTTPException(status_code=404, detail="La zona protegida enviada no existe en la BD.")

    # 2. Evaluar riesgo con nuestros modelos pre-entrenados
    ml_result = evaluate_risk(
        temp=request.temperatura,
        hum=request.humedad,
        wind=request.viento,
        prec=request.precipitacion
    )
    
    nivel_riesgo = ml_result["nivel_riesgo"]
    detalles = ml_result["detalles"]

    # 3. Generar directiva automática con NLP
    directiva = generate_directive(
        nivel_riesgo=nivel_riesgo,
        temp=request.temperatura,
        hum=request.humedad,
        viento=request.viento
    )

    # 4. Almacenar el histórico de inferencia en la base de datos (Trazabilidad)
    nueva_prediccion = PrediccionRiesgo(
        id_zona=request.id_zona,
        nivel_riesgo=nivel_riesgo,
        resultados_json=detalles,
        directiva_nlp=directiva
    )
    
    db.add(nueva_prediccion)
    db.commit()
    db.refresh(nueva_prediccion)

    # 5. Retornar el payload final al cliente
    return PredictionResponse(
        id_prediccion=nueva_prediccion.id_prediccion,
        nivel_riesgo=nueva_prediccion.nivel_riesgo,
        detalles_modelos=nueva_prediccion.resultados_json,
        directiva_accion=nueva_prediccion.directiva_nlp,
        fecha_evaluacion=nueva_prediccion.fecha_evaluacion
    )

@router.get("/history", response_model=List[PredictionResponse])
def get_prediction_history(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):

    predicciones = db.query(PrediccionRiesgo).order_by(PrediccionRiesgo.fecha_evaluacion.desc()).offset(skip).limit(limit).all()
    
    resultados = []
    for p in predicciones:
        resultados.append(
            PredictionResponse(
                id_prediccion=p.id_prediccion,
                nivel_riesgo=p.nivel_riesgo,
                detalles_modelos=p.resultados_json,
                directiva_accion=p.directiva_nlp,
                fecha_evaluacion=p.fecha_evaluacion
            )
        )
    return resultados
