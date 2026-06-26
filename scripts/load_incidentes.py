import os
import sys
import pandas as pd
import geopandas as gpd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Agregar raíz al path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Cargar variables de entorno
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL no está definida.")
    sys.exit(1)

def load_incidentes():
    engine = create_engine(DATABASE_URL)
    
    # Rutas
    data_dir = Path(__file__).resolve().parent.parent / "data"
    csv_path = data_dir / "estadisticasincendiosforestales2015-2024.csv"
    
    if not csv_path.exists():
        print(f"Error: No se encontró {csv_path}")
        return
        
    print("Cargando CSV de incidentes...")
    df = pd.read_csv(csv_path, low_memory=False)
    
    # Filtrar por Chiapas para reducir datos
    df_chiapas = df[df['Estado'] == 'Chiapas'].copy()
    
    # Limpiar coordenadas (asegurar que sean números y no nulos)
    df_chiapas['latitud'] = pd.to_numeric(df_chiapas['latitud'], errors='coerce')
    df_chiapas['longitud'] = pd.to_numeric(df_chiapas['longitud'], errors='coerce')
    df_chiapas = df_chiapas.dropna(subset=['latitud', 'longitud', 'Fecha_Inicio'])
    
    print(f"Procesando {len(df_chiapas)} incidentes en Chiapas...")
    
    # Convertir a GeoDataFrame
    gdf_incidentes = gpd.GeoDataFrame(
        df_chiapas, 
        geometry=gpd.points_from_xy(df_chiapas.longitud, df_chiapas.latitud),
        crs="EPSG:4326"
    )
    
    # Cargar Zonas Protegidas desde la BD
    gdf_zonas = gpd.read_postgis("SELECT id_zona, nombre, geometria as geometry FROM zonas_protegidas", engine, geom_col='geometry')
    
    if gdf_zonas.empty:
        print("No hay zonas protegidas en la base de datos.")
        return
        
    print("Realizando Join Espacial (puntos dentro de polígonos)...")
    # Spatial join: Puntos de incendios que caen dentro de Zonas Protegidas
    join_result = gpd.sjoin(gdf_incidentes, gdf_zonas, how="inner", predicate="intersects")
    
    if join_result.empty:
        print("Ningún incidente cayó dentro de las zonas protegidas.")
        return
        
    print(f"Se encontraron {len(join_result)} incidentes dentro de las Zonas Protegidas.")
    
    # Insertar en la BD
    with engine.begin() as conn:
        # Limpiar tabla previa si existieran para evitar duplicados
        conn.execute(text("TRUNCATE TABLE incidentes_historicos RESTART IDENTITY CASCADE"))
        
        import uuid
        insert_query = text("""
            INSERT INTO incidentes_historicos (id_incidente, id_zona, fecha_deteccion, fuente, coordenada) 
            VALUES (:id_incidente, :id_zona, :fecha, :fuente, ST_GeomFromText(:geom_wkt, 4326))
        """)
        
        count = 0
        for idx, row in join_result.iterrows():
            try:
                # Validar fecha
                fecha = pd.to_datetime(row['Fecha_Inicio'])
                # Fuente de los datos
                fuente = "CONAFOR"
                # Extraer id_zona del sjoin
                id_zona = row['id_zona']
                
                conn.execute(insert_query, {
                    "id_incidente": str(uuid.uuid4()),
                    "id_zona": id_zona,
                    "fecha": fecha,
                    "fuente": fuente,
                    "geom_wkt": row.geometry.wkt
                })
                count += 1
            except Exception as e:
                print(f"Error insertando fila: {e}")
                
    print(f"¡Éxito! Se insertaron {count} incidentes históricos en la tabla Incidentes_Historicos.")

if __name__ == "__main__":
    load_incidentes()
