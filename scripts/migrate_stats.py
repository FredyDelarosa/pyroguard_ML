import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Cargar variables de entorno
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

# 1. Agregar las columnas a la BD si no existen
alter_queries = [
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS temp_mean FLOAT DEFAULT 0.0;",
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS temp_std FLOAT DEFAULT 1.0;",
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS hum_mean FLOAT DEFAULT 0.0;",
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS hum_std FLOAT DEFAULT 1.0;",
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS viento_mean FLOAT DEFAULT 0.0;",
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS viento_std FLOAT DEFAULT 1.0;",
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS prec_mean FLOAT DEFAULT 0.0;",
    "ALTER TABLE zonas_protegidas ADD COLUMN IF NOT EXISTS prec_std FLOAT DEFAULT 1.0;"
]

with engine.begin() as conn:
    for q in alter_queries:
        conn.execute(text(q))

# 2. Calcular estadísticas globales del dataset actual
csv_path = Path(__file__).resolve().parent.parent / "data" / "dataset_ML_preparado.csv"
df = pd.read_csv(csv_path)

stats = {
    'temp_mean': float(df['temp_max'].mean()),
    'temp_std': float(df['temp_max'].std()),
    'hum_mean': float(df['humedad_media'].mean()),
    'hum_std': float(df['humedad_media'].std()),
    'viento_mean': float(df['viento_max'].mean()),
    'viento_std': float(df['viento_max'].std()),
    'prec_mean': float(df['precipitacion'].mean()),
    'prec_std': float(df['precipitacion'].std()),
}

print("Estadísticas Base Calculadas:")
print(stats)

# 3. Asignar estas estadísticas base a las zonas existentes (simulando microclimas con leve ruido)
with engine.begin() as conn:
    zonas = conn.execute(text("SELECT id_zona, nombre FROM zonas_protegidas")).fetchall()
    for z in zonas:
        # Añadimos un ruido muy pequeño para simular diferencias de microclima entre reservas
        t_m = stats['temp_mean'] + np.random.uniform(-3.0, 3.0)
        h_m = stats['hum_mean'] + np.random.uniform(-10.0, 10.0)
        
        upd = text("""
            UPDATE zonas_protegidas SET
                temp_mean = :t_m, temp_std = :t_s,
                hum_mean = :h_m, hum_std = :h_s,
                viento_mean = :v_m, viento_std = :v_s,
                prec_mean = :p_m, prec_std = :p_s
            WHERE id_zona = :id
        """)
        conn.execute(upd, {
            't_m': t_m, 't_s': stats['temp_std'],
            'h_m': h_m, 'h_s': stats['hum_std'],
            'v_m': stats['viento_mean'], 'v_s': stats['viento_std'],
            'p_m': stats['prec_mean'], 'p_s': stats['prec_std'],
            'id': z.id_zona
        })
        
print("Base de datos migrada exitosamente.")
