import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.rules_engine import ReportRulesEngine

def main():
    print("Iniciando Motor de Reglas...")
    engine = ReportRulesEngine()
    
    # Simulamos que ml_service.py nos envió su evaluación final:
    ml_payload = {
        "nivel_riesgo": "Crítico",
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
    
    print("\n--- Payload Recibido del ML ---")
    print(json.dumps(ml_payload, indent=2))
    
    print("\nEvaluando Reglas y Recuperando Contexto (RAG)...")
    contexto_final = engine.build_system_context(ml_payload)
    
    print("\n=== CONTEXTO FINAL GENERADO PARA EL LLM ===")
    print(json.dumps(contexto_final, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
