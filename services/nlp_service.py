import os

# Intento de importar módulos de LangChain (Si no está configurado, usamos fallback)
try:
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import ChatOpenAI
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

def generate_directive(nivel_riesgo: str, temp: float, hum: float, viento: float) -> str:
    """
    Genera una directiva técnica en lenguaje natural utilizando LangChain.
    Si no hay una API Key de OpenAI configurada en el .env, devuelve una respuesta determinista.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if HAS_LANGCHAIN and api_key:
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, openai_api_key=api_key)
        
        template = """
        Eres un asistente de la CONAFOR experto en mitigación de incendios forestales. 
        Las condiciones climáticas actuales detectadas en la reserva son: 
        - Temperatura: {temp}°C
        - Humedad: {hum}%
        - Viento: {viento} km/h
        
        El modelo matemático ha clasificado el Nivel de Riesgo como: {riesgo}.
        
        Redacta una directiva técnica, urgente y breve (máximo 3 líneas) indicando a los guardabosques 
        qué acciones inmediatas deben tomar basándose exclusivamente en este nivel de riesgo.
        """
        
        prompt = PromptTemplate(
            input_variables=["temp", "hum", "viento", "riesgo"],
            template=template
        )
        
        chain = prompt | llm | StrOutputParser()
        
        try:
            resultado = chain.invoke({
                "temp": temp,
                "hum": hum,
                "viento": viento,
                "riesgo": nivel_riesgo
            })
            return resultado
        except Exception as e:
            return f"[Error API LLM]: No se pudo generar directiva dinámica. Detalle: {str(e)}"
    
    else:
        # Fallback predeterminado si no hay configuración de LLM o API Key
        if nivel_riesgo == "Crítico":
            return "ALERTA MÁXIMA: Movilizar brigadas de respuesta rápida inmediatamente. Riesgo inminente de ignición por condiciones extremas."
        elif nivel_riesgo == "Alto":
            return "ALERTA: Incrementar patrullajes en zonas vulnerables y brechas cortafuego. Preparar equipo contraincendios."
        elif nivel_riesgo == "Medio":
            return "PRECAUCIÓN: Monitorear reportes ciudadanos y mantener vigilancia constante en puntos históricamente secos."
        else:
            return "CONDICIONES SEGURAS: Riesgo de incendio mínimo. Continuar con actividades de rutina y mantenimiento."
