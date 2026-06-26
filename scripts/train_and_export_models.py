import os
import sys
from pathlib import Path
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
import joblib

# Configurar rutas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "dataset_ML_preparado.csv"
MODELS_DIR = PROJECT_ROOT / "models"

def train_and_export():
    if not DATA_PATH.exists():
        print(f"Error: No se encontró el dataset en {DATA_PATH}")
        sys.exit(1)

    print("Cargando dataset preparado desde EDA...")
    df = pd.read_csv(DATA_PATH)

    # Definir las variables climáticas base que utiliza el modelo
    features = ['temp_max', 'humedad_media', 'viento_max', 'precipitacion']
    
    # Verificar que existan en el CSV
    for f in features:
        if f not in df.columns:
            print(f"Error: Falta la columna {f} en el dataset.")
            sys.exit(1)

    X = df[features].copy()

    # 1. Escalamiento de datos
    print("Entrenando StandardScaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 2. Entrenamiento K-Means (Contexto de riesgo)
    print("Entrenando K-Means (n_clusters=4)...")
    # Utilizamos n_init='auto' recomendado en scikit-learn reciente
    kmeans = KMeans(n_clusters=4, random_state=42, n_init='auto')
    kmeans.fit(X_scaled)

    # 3. Entrenamiento Isolation Forest (Anomalías)
    print("Entrenando Isolation Forest (contamination=0.05)...")
    iso_forest = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    iso_forest.fit(X_scaled)

    # 4. Exportar Modelos
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    scaler_path = MODELS_DIR / "scaler.joblib"
    kmeans_path = MODELS_DIR / "kmeans.joblib"
    iso_path = MODELS_DIR / "iso_forest.joblib"

    print("Exportando modelos a /ML/models/ ...")
    joblib.dump(scaler, scaler_path)
    joblib.dump(kmeans, kmeans_path)
    joblib.dump(iso_forest, iso_path)

    print("\n¡Entrenamiento y exportación completados con éxito!")
    print(f" - {scaler_path.name}")
    print(f" - {kmeans_path.name}")
    print(f" - {iso_path.name}")

if __name__ == "__main__":
    train_and_export()
