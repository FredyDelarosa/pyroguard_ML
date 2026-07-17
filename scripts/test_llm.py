import json
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.rules_engine import ReportRulesEngine
from services.llm_service import ReportGeneratorLLM

def main():
    print("============================================")
    print(" PIPELINE COMPLETO: RAG + MOTOR + LLM")
    print("============================================\n")
    
    # 1. Simulación de datos provenientes de la API y de K-Means
    ml_payload = {
        "nivel_riesgo": "Crítico",
        "zona_nombre": "La Sepultura", # Simulamos una reserva real
        "detalles": {
            "kmeans_cluster": 3,
            "isolation_forest_anomaly": -1,
            "anomaly_score": -0.15
        },
        "meteo_data": {
            "temp": 38.5,
            "hum": 12,
            "wind": 45
        }
    }
    
    print("1. Ejecutando Motor de Reglas e Inyección de Contexto (RAG)...")
    engine = ReportRulesEngine()
    contexto_final = engine.build_system_context(ml_payload)
    print("   [OK] Contexto estructurado y fragmentos de Protección Civil extraídos.\n")
    
    print("2. Cargando Inteligencia Artificial (Llama-3)...")
    start_time = time.time()
    # Si la descarga falló o no existe, fallará aquí con claridad
    generator = ReportGeneratorLLM() 
    print(f"   [OK] Modelo cargado en RAM ({time.time() - start_time:.2f} segundos).\n")
    
    print("3. Generando Reporte (Esto tomará unos segundos dependiendo del CPU)...")
    start_time = time.time()
    reporte_json = generator.generate_report_json(contexto_final)
    print(f"   [OK] Reporte generado ({time.time() - start_time:.2f} segundos).\n")
    
    print("============================================")
    print(" REPORTE FINAL (JSON PURO PARA BACKEND) ")
    print("============================================")
    print(json.dumps(reporte_json, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
