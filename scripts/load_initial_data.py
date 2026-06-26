import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import geopandas as gpd
from sqlalchemy import create_engine, text

# Agregar la raíz del proyecto ML al path para poder importar módulos futuros
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Cargar variables de entorno desde el archivo .env
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL no está definida. Por favor, crea el archivo ML/.env basado en ML/.env.example")
    sys.exit(1)

def load_reserves():
    engine = create_engine(DATABASE_URL)
    
    # Ruta relativa para alcanzar la carpeta data que ahora está dentro de ML/
    geojson_path = Path(__file__).resolve().parent.parent / "data" / "reservas_objetivo" / "reservas_chiapas.geojson"
    
    if not geojson_path.exists():
        print(f"Error: No se encontró el archivo {geojson_path}")
        print("Asegúrate de que el archivo reservas_chiapas.geojson fue generado correctamente en el EDA.")
        return

    print(f"Conectando a la base de datos...")
    print(f"Cargando polígonos desde {geojson_path.name}...")
    
    # Leer el archivo generado en la fase EDA
    gdf = gpd.read_file(geojson_path)
    
    # Calcular el area aproximada en hectareas
    # Convertimos temporalmente a una proyección cilíndrica de igual área para medir bien
    gdf_proj = gdf.to_crs("+proj=cea")
    gdf['area_hectareas'] = gdf_proj.geometry.area / 10000

    # Iniciar transacción
    with engine.begin() as conn:
        for idx, row in gdf.iterrows():
            nombre = row.get("NOMBRE", f"Reserva_{idx}")
            area = row['area_hectareas']
            # Convertir geometría a formato WKT (Well-Known Text)
            geom_wkt = row.geometry.wkt
            
            # Verificar si ya insertamos esta reserva antes
            check_query = text("SELECT COUNT(*) FROM Zonas_Protegidas WHERE nombre = :nombre")
            count = conn.execute(check_query, {"nombre": nombre}).scalar()
            
            if count == 0:
                print(f"Insertando: {nombre} ({area:.2f} ha)...")
                # Se utiliza ST_GeomFromText de PostGIS indicando el SRID 4326 (WGS84)
                import uuid
                insert_query = text("""
                    INSERT INTO Zonas_Protegidas (id_zona, nombre, geometria, area_hectareas) 
                    VALUES (:id_zona, :nombre, ST_GeomFromText(:geom_wkt, 4326), :area)
                """)
                conn.execute(insert_query, {"id_zona": str(uuid.uuid4()), "nombre": nombre, "geom_wkt": geom_wkt, "area": area})
            else:
                print(f"Omitiendo: La reserva '{nombre}' ya existe en la base de datos.")
                
    print("\n¡Ingesta de Zonas Protegidas completada con éxito!")

if __name__ == "__main__":
    load_reserves()
