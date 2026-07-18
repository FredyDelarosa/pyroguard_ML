import os
import json
from llama_cpp import Llama

class ReportGeneratorLLM:
    def __init__(self, model_path="/app/modelos_locales/Llama-3-8B-Instruct.Q4_K_M.gguf"):
        self.model_path = model_path
        print(f"Cargando motor Llama en memoria desde {self.model_path}...")
        
        # Inicializamos Llama (Optimizado para correr en CPU)
        # n_ctx=2048 es el tamaño máximo de tokens (suficiente para nuestros RAGs cortos)
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=4096, # Contexto aumentado para manejar prompts y respuestas más largas
            n_threads=os.cpu_count() or 4,
            verbose=False # Apagamos los logs internos que ensucian la consola
        )

    def generate_report_json(self, context_packet: dict) -> dict:
        """
        Toma el Paquete de Conocimiento del RAG/Reglas y le pide a Llama 3 
        que redacte el reporte forzando la salida en formato JSON puro.
        """
        
        # 1. Definimos la estructura exacta que queremos que Llama llene
        schema_json = {
            "type": "object",
            "properties": {
                "resumen_ejecutivo": {"type": "string", "description": "Breve narrativa de la situación actual basada en la meteorología."},
                "analisis_de_riesgo": {"type": "string", "description": "Explicación del nivel de riesgo y la severidad de la anomalía."},
                "justificacion_protocolo": {"type": "string", "description": "Justificación de las acciones basándose en la literatura de protección civil y en los incidentes históricos de referencia proporcionados."},
                "acciones_tacticas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "orden": {"type": "integer"},
                            "accion": {"type": "string"},
                            "fuente": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["resumen_ejecutivo", "analisis_de_riesgo", "justificacion_protocolo", "acciones_tacticas"]
        }

        # 2. Construimos el System Prompt de contención
        system_prompt = f"""
Eres un analista experto de Protección Civil especializado en redactar reportes técnicos narrativos y analíticos muy detallados.
Tu trabajo es escribir párrafos formales, argumentativos y profesionales, NO simples títulos o palabras sueltas.

[PAQUETE DE DATOS OBLIGATORIOS]
{json.dumps(context_packet, ensure_ascii=False, indent=2)}

INSTRUCCIONES CRÍTICAS PARA EL JSON:
1. 'resumen_ejecutivo': Redacta un párrafo completo (mínimo 4 líneas) analizando la situación actual basándote en los 'datos_meteorologicos' y la 'regla_inquebrantable'. Si el riesgo es BAJO, enfatiza de forma clara que las condiciones son seguras y no hay anomalías.
2. 'analisis_de_riesgo': Redacta un párrafo detallando el Nivel de Riesgo asignado. Jamás inventes peligro si el riesgo de la regla inquebrantable es Bajo.
3. 'justificacion_protocolo': Redacta un párrafo argumentativo citando el 'contexto_proteccion_civil' y el 'contexto_historico_real'.
4. 'acciones_tacticas': Genera la lista de acciones precisas correspondientes al nivel de riesgo, con su respectiva 'fuente'. No inventes tácticas de combate al fuego si el riesgo es bajo (enfócate en el mantenimiento rutinario).

Debes responder ÚNICAMENTE con un objeto JSON válido que respete el esquema proporcionado. No escribas texto introductorio.
"""

        print("Enviando contexto al LLM para inferencia (generando redacción)...")
        
        # 3. Llamada al motor LLM (Inferencia)
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Genera el reporte final en formato JSON."}
            ],
            response_format={
                "type": "json_object",
                "schema": schema_json
            },
            temperature=0.1, # Muy baja temperatura para evitar alucinaciones, queremos precisión
            max_tokens=1500 # Incrementado para evitar que el JSON se corte a medias
        )

        # Extraemos el string JSON de la respuesta y lo convertimos a diccionario de Python
        try:
            json_response_str = response['choices'][0]['message']['content']
            final_report = json.loads(json_response_str)
            
            # Le inyectamos los metadatos fijos antes de devolverlo
            final_report["evaluacion_matematica"] = context_packet["analisis_matematico"]
            return final_report
            
        except Exception as e:
            print(f"Error procesando la respuesta del LLM: {e}")
            return {"error": "El modelo no devolvió un JSON válido.", "raw": response['choices'][0]['message']['content']}
