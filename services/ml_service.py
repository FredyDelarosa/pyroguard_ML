import joblib
import numpy as np
from pathlib import Path

# Definir la ruta a los modelos exportados
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

try:
    scaler = joblib.load(MODELS_DIR / "scaler.joblib")
    kmeans = joblib.load(MODELS_DIR / "kmeans.joblib")
    iso_forest = joblib.load(MODELS_DIR / "iso_forest.joblib")
except FileNotFoundError:
    raise RuntimeError("No se encontraron los archivos .joblib en la carpeta ML/models/.")

def evaluate_risk(temp: float, hum: float, wind: float, prec: float) -> dict:

    # 1. Preparar el vector de entrada en el orden exacto de entrenamiento
    input_data = np.array([[temp, hum, wind, prec]])
    
    # 2. Escalar datos
    scaled_data = scaler.transform(input_data)
    
    # 3. Inferencia K-Means (Devuelve el ID del clúster)
    cluster_id = int(kmeans.predict(scaled_data)[0])
    
    # 4. Inferencia Isolation Forest (-1 = Anomalía Extrema, 1 = Normal)
    is_anomaly = int(iso_forest.predict(scaled_data)[0])
    anomaly_score = float(iso_forest.decision_function(scaled_data)[0])
    
    # 5. Lógica de Reglas de Negocio (Híbrida)
    # Como los IDs de los clústeres de K-Means varían dinámicamente,
    # utilizamos una combinación de la detección de anomalías y umbrales climáticos críticos.
    nivel_riesgo = "Bajo"
    
    from .threshold_manager import load_thresholds
    umbrales = load_thresholds()
    
    if is_anomaly == -1:
        # El algoritmo detectó un clima estadísticamente extremo para la zona
        if temp >= umbrales["critico"]["temp"] and hum <= umbrales["critico"]["hum"]:
            nivel_riesgo = "Crítico"
        else:
            nivel_riesgo = "Alto"
    else:
        # El clima es estadísticamente normal, pero verificamos riesgo estacional
        if temp >= umbrales["medio"]["temp"] and hum <= umbrales["medio"]["hum"]:
            nivel_riesgo = "Medio"
        else:
            nivel_riesgo = "Bajo"

    return {
        "nivel_riesgo": nivel_riesgo,
        "detalles": {
            "kmeans_cluster": cluster_id,
            "isolation_forest_anomaly": is_anomaly,
            "anomaly_score": round(anomaly_score, 4)
        }
    }
