from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import predict, analitica, zonas

from database.connection import engine
from database.models import Base

# Crear las tablas en la BD si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PyroGuard AI - API",
    description="Microservicio RESTful de Inteligencia Artificial para la predicción de incendios forestales usando Machine Learning Híbrido (K-Means + Isolation Forest) y LangChain.",
    version="1.0.0"
)

# Configuración de CORS (Permite conexiones desde cualquier frontend en desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar Endpoints
app.include_router(predict.router, prefix="/api/v1/predict", tags=["Predicciones ML"])
app.include_router(analitica.router, prefix="/api/v1/analitica", tags=["Analítica Técnica (Modelos e Históricos)"])
app.include_router(zonas.router, prefix="/api/v1/zonas", tags=["Zonas Protegidas (PostGIS)"])

@app.get("/")
def read_root():
    """Endpoint de salud del servidor."""
    return {
        "status": "online",
        "service": "PyroGuard AI Backend",
        "docs": "/docs",
        "message": "Servidor operando correctamente. Modelos ML cargados en memoria."
    }

if __name__ == "__main__":
    import uvicorn
    # Lanzar el servidor en desarrollo local
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
