import joblib
import numpy as np
from pathlib import Path

# Definir la ruta a los modelos exportados
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

try:
    kmeans = joblib.load(MODELS_DIR / "kmeans.joblib")
    iso_forest = joblib.load(MODELS_DIR / "iso_forest.joblib")
except FileNotFoundError:
    raise RuntimeError("No se encontraron los archivos .joblib en la carpeta ML/models/.")

def evaluate_risk(temp: float, hum: float, wind: float, prec: float, stats: dict = None) -> dict:

    if stats is None:
        # Valores de respaldo en caso de que no se pase una zona (Global de Chiapas)
        stats = {
            'temp_mean': 20.30, 'temp_std': 2.07,
            'hum_mean': 80.49, 'hum_std': 9.76,
            'viento_mean': 10.46, 'viento_std': 4.52,
            'prec_mean': 5.34, 'prec_std': 10.69
        }

    # 1. Calcular Z-Scores manuales (Local Scaling)
    temp_z = (temp - stats['temp_mean']) / (stats['temp_std'] if stats['temp_std'] > 0 else 1.0)
    hum_z = (hum - stats['hum_mean']) / (stats['hum_std'] if stats['hum_std'] > 0 else 1.0)
    wind_z = (wind - stats['viento_mean']) / (stats['viento_std'] if stats['viento_std'] > 0 else 1.0)
    prec_z = (prec - stats['prec_mean']) / (stats['prec_std'] if stats['prec_std'] > 0 else 1.0)
    
    scaled_data = np.array([[temp_z, hum_z, wind_z, prec_z]])
    
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
