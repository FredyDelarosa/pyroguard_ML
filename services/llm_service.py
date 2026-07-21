import os
import json
import requests
from llama_cpp import Llama

class ReportGeneratorLLM:
    def __init__(self, model_path="/app/modelos_locales/Llama-3-8B-Instruct.Q4_K_M.gguf"):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        if self.groq_api_key:
            print("Iniciando LLM usando Groq Cloud API (Modo Ultra-Rápido)...")
            self.llm = None
        else:
            self.model_path = model_path
            print(f"Cargando motor Llama en memoria desde {self.model_path} (Modo CPU Local)...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,
                n_threads=os.cpu_count() or 4,
                verbose=False
            )

    def generate_report_json(self, context_packet: dict) -> dict:
        schema_json = {
            "type": "object",
            "properties": {
                "resumen_ejecutivo": {"type": "string"},
                "analisis_de_riesgo": {"type": "string"},
                "justificacion_protocolo": {"type": "string"},
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

        system_prompt = f"""
Eres un analista experto de Protección Civil especializado en redactar reportes técnicos narrativos y analíticos muy detallados.
Tu trabajo es escribir párrafos formales, argumentativos y profesionales, NO simples títulos o palabras sueltas.

[PAQUETE DE DATOS OBLIGATORIOS]
{json.dumps(context_packet, ensure_ascii=False, indent=2)}

INSTRUCCIONES CRÍTICAS PARA EL JSON:
1. 'resumen_ejecutivo': Redacta un párrafo completo analizando la meteorología. Si el nivel de riesgo es BAJO, enfatiza que las condiciones son seguras. PROHIBIDO mencionar términos internos como "regla inquebrantable" o "análisis matemático".
2. 'analisis_de_riesgo': Explica el Nivel de Riesgo asignado. Jamás inventes peligro si el riesgo oficial es Bajo. Redacta de forma natural para el usuario final.
3. 'justificacion_protocolo': Argumenta las acciones usando el 'contexto_proteccion_civil' y el 'contexto_historico_real'.
4. 'acciones_tacticas': Extrae una lista de acciones precisas ÚNICAMENTE a partir del texto proporcionado en 'contexto_proteccion_civil'. Como 'fuente', debes usar el nombre del manual o documento oficial mencionado en el contexto (NUNCA uses "Regla Inquebrantable" o tu propio conocimiento como fuente). Si el riesgo es bajo, extrae acciones preventivas o de monitoreo del contexto.

Debes responder ÚNICAMENTE con un objeto JSON válido que respete el esquema proporcionado. No escribas texto introductorio.
"""
        print("Enviando contexto al LLM para inferencia (generando redacción)...")
        
        try:
            if self.groq_api_key:
                # Inferencia ultrarrápida (Groq Cloud)
                headers = {
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama3-8b-8192",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Genera el reporte final en formato JSON respetando estrictamente el esquema."}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                    "max_tokens": 1500
                }
                resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                json_response_str = resp.json()['choices'][0]['message']['content']
            else:
                # Inferencia lenta (CPU Local)
                response = self.llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Genera el reporte final en formato JSON."}
                    ],
                    response_format={
                        "type": "json_object",
                        "schema": schema_json
                    },
                    temperature=0.1,
                    max_tokens=1500
                )
                json_response_str = response['choices'][0]['message']['content']

            final_report = json.loads(json_response_str)
            final_report["evaluacion_matematica"] = context_packet["analisis_matematico"]
            return final_report
            
        except Exception as e:
            print(f"Error procesando la respuesta del LLM: {e}")
            return {"error": "El modelo no devolvió un JSON válido.", "raw": str(e)}
