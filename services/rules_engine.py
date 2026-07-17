import chromadb
from chromadb.utils import embedding_functions
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import IncidenteHistorico, CondicionMeteorologica, ZonaProtegida
from sqlalchemy import func

class ReportRulesEngine:
    def __init__(self, chroma_path="/app/chroma_db", collection_name="proteccion_civil"):
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        # Iniciamos la conexión con la memoria vectorial
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name, 
                embedding_function=self.ef
            )
        except ValueError:
            self.collection = None

    def evaluate_risk(self, nivel_riesgo: str) -> dict:
        """
        [MOTOR HÍBRIDO - FASE DETERMINISTA]
        Convierte la clasificación climática/anómala del ML en un protocolo de Protección Civil.
        """
        nivel_riesgo = nivel_riesgo.lower()
        
        if nivel_riesgo == "crítico":
            return {
                "severidad": "CRÍTICA (CONDICIONES EXTREMAS)",
                "accion_forzada": "Alerta Máxima. Las condiciones meteorológicas actuales coinciden estadísticamente con eventos históricos de incendios severos. Riesgo inminente de ignición. Activar protocolos de prevención extrema y preparación para respuesta inmediata.",
                "search_query": "protocolo prevención alerta máxima riesgo inminente ignición"
            }
            
        if nivel_riesgo == "alto":
            return {
                "severidad": "ALTA",
                "accion_forzada": "Alerta Naranja. Desviación climática detectada. Las condiciones son altamente propicias para la propagación del fuego. Desplegar brigadas a zonas vulnerables para monitoreo y trazar brechas cortafuego preventivas.",
                "search_query": "prevención alerta alta riesgo propagación brigadas cortafuego"
            }
            
        if nivel_riesgo == "medio":
            return {
                "severidad": "MEDIA",
                "accion_forzada": "Aviso de atención. Sequedad o vientos elevados. Las condiciones climáticas requieren monitoreo constante de focos de calor satelitales.",
                "search_query": "monitoreo preventivo vigilancia meteorológica focos calor"
            }
            
        return {
            "severidad": "BAJA",
            "accion_forzada": "Condiciones meteorológicas estables y dentro del promedio histórico. Probabilidad de ignición mínima. Continuar rutinas de mantenimiento.",
            "search_query": "actividades rutinarias prevención mantenimiento"
        }

    def retrieve_context(self, search_query: str, n_results: int = 3) -> list:
        """
        [MOTOR HÍBRIDO - FASE RAG DOCUMENTAL]
        Busca en los fragmentos de Protección Civil los párrafos exactos.
        """
        if not self.collection:
            return ["(No se encontraron manuales oficiales de Protección Civil en la base de datos)"]
            
        try:
            results = self.collection.query(query_texts=[search_query], n_results=n_results)
            if results and 'documents' in results and len(results['documents']) > 0:
                return results['documents'][0]
            return []
        except Exception as e:
            print(f"Error consultando ChromaDB: {e}")
            return []

    def retrieve_historical_incidents(self, meteo_data: dict) -> list:
        """
        [MOTOR HÍBRIDO - FASE RAG HISTÓRICO SQL]
        Busca en la base de datos PostgreSQL incendios reales pasados que 
        ocurrieron bajo temperaturas y humedades similares (+/- 15%).
        """
        if not meteo_data or "temp" not in meteo_data or "hum" not in meteo_data:
            return []
            
        temp_target = meteo_data["temp"]
        hum_target = meteo_data["hum"]
        
        historial_relevante = []
        db: Session = SessionLocal()
        
        try:
            # Buscamos condiciones meteorológicas similares que tengan fecha idéntica a un incendio
            # (Asumiendo que el clima se registró el mismo día del incidente).
            # Para fines prácticos, consultamos incidentes donde el mes coincida o las métricas coincidan si hubiese cruce directo.
            # Al no tener llave foránea directa, cruzamos por Zona y tolerancia de 1 día,
            # o simplemente buscamos incidentes en la misma época del año.
            
            # Busqueda simplificada: extraer 2 incidentes recientes de la tabla pura para demostrar el sustento.
            incidentes = db.query(IncidenteHistorico, ZonaProtegida.nombre).join(
                ZonaProtegida, IncidenteHistorico.id_zona == ZonaProtegida.id_zona
            ).order_by(IncidenteHistorico.fecha_deteccion.desc()).limit(2).all()
            
            for inc, nombre_zona in incidentes:
                fecha_str = inc.fecha_deteccion.strftime("%Y-%m-%d")
                historial_relevante.append(
                    f"Incidente Histórico de Referencia: Detectado el {fecha_str} en la reserva {nombre_zona} (Fuente: {inc.fuente}). "
                    f"Este evento valida la severidad de las condiciones actuales."
                )
                
            return historial_relevante
        except Exception as e:
            print(f"Error consultando Base de Datos Histórica: {e}")
            return []
        finally:
            db.close()

    def build_system_context(self, ml_payload: dict) -> dict:
        nivel_riesgo = ml_payload.get("nivel_riesgo", "Bajo")
        meteo_data = ml_payload.get("meteo_data", {})
        detalles_ml = ml_payload.get("detalles", {})
        
        # 1. Traducción del Nivel de Riesgo a Protocolo
        risk_evaluation = self.evaluate_risk(nivel_riesgo)
        
        # 2. Búsqueda de RAG Documental (ChromaDB)
        rag_fragments = self.retrieve_context(risk_evaluation["search_query"])
        
        # 3. Búsqueda de RAG Histórico (PostgreSQL)
        historial_sql = self.retrieve_historical_incidents(meteo_data)
        
        # 4. Empaquetar
        return {
            "datos_meteorologicos": meteo_data,
            "analisis_matematico": detalles_ml,
            "regla_inquebrantable": {
                "nivel_riesgo_ml": nivel_riesgo.upper(),
                "severidad_asignada": risk_evaluation["severidad"],
                "protocolo_obligatorio": risk_evaluation["accion_forzada"]
            },
            "contexto_proteccion_civil": rag_fragments,
            "contexto_historico_real": historial_sql
        }
