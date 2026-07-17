import chromadb
from chromadb.utils import embedding_functions

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
            self.collection = None # Por si aún no hay manuales cargados

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
            
        # Nivel "Bajo"
        return {
            "severidad": "BAJA",
            "accion_forzada": "Condiciones meteorológicas estables y dentro del promedio histórico. Probabilidad de ignición mínima. Continuar rutinas de mantenimiento.",
            "search_query": "actividades rutinarias prevención mantenimiento"
        }

    def retrieve_context(self, search_query: str, n_results: int = 3) -> list:
        """
        [MOTOR HÍBRIDO - FASE RAG]
        Busca en los fragmentos de Protección Civil los párrafos exactos.
        """
        if not self.collection:
            return ["(No se encontraron manuales oficiales de Protección Civil en la base de datos)"]
            
        try:
            results = self.collection.query(
                query_texts=[search_query],
                n_results=n_results
            )
            
            if results and 'documents' in results and len(results['documents']) > 0:
                return results['documents'][0]
            return []
        except Exception as e:
            print(f"Error consultando ChromaDB: {e}")
            return []

    def build_system_context(self, ml_payload: dict) -> dict:
        """
        Construye el 'Paquete de Conocimiento' inyectable al LLM.
        Asume que ml_payload contiene el 'nivel_riesgo' pre-calculado por ml_service.
        """
        nivel_riesgo = ml_payload.get("nivel_riesgo", "Bajo")
        meteo_data = ml_payload.get("meteo_data", {})
        detalles_ml = ml_payload.get("detalles", {})
        
        # 1. Traducción del Nivel de Riesgo a Protocolo
        risk_evaluation = self.evaluate_risk(nivel_riesgo)
        
        # 2. Búsqueda de RAG basada en el protocolo
        rag_fragments = self.retrieve_context(risk_evaluation["search_query"])
        
        # 3. Empaquetar
        return {
            "datos_meteorologicos": meteo_data,
            "analisis_matematico": detalles_ml,
            "regla_inquebrantable": {
                "nivel_riesgo_ml": nivel_riesgo.upper(),
                "severidad_asignada": risk_evaluation["severidad"],
                "protocolo_obligatorio": risk_evaluation["accion_forzada"]
            },
            "contexto_proteccion_civil": rag_fragments
        }
