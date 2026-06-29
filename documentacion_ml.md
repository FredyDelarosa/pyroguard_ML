# Documentación del Microservicio de Machine Learning (Minería de Datos)

El microservicio de Minería de Datos de **PyroGuard AI** es el núcleo analítico de la plataforma. Está construido con una Arquitectura Limpia basada en **FastAPI**, interactúa directamente con **PostGIS** para el almacenamiento espacial, y emplea tareas asíncronas con **Celery** y **Redis**.

## Componentes Principales

### 1. APIs y Enrutadores (FastAPI)
- **Predict Router (`/predict`)**: Recibe peticiones para evaluar el riesgo de incendio forestal. Orquesta la recolección de datos climáticos, invoca los modelos matemáticos y retorna el nivel de riesgo y la directiva de acción generada.
- **Zonas Router (`/zonas`)**: Gestiona los polígonos geográficos de las Zonas Protegidas. Emplea las funciones geoespaciales de PostGIS (`ST_AsGeoJSON`, `ST_Area`, `ST_GeomFromGeoJSON`) para almacenar y servir las coordenadas y áreas. Incluye un endpoint optimizado para el portal ciudadano que devuelve exclusivamente las alertas vigentes sin exponer métricas científicas.

### 2. Servicios de Inteligencia Artificial
- **ML Service**: Contiene los modelos pre-entrenados para la evaluación de riesgo.
  - *Isolation Forest*: Identifica anomalías climáticas extremas.
  - *KMeans*: Agrupa las condiciones climáticas para clasificar el riesgo en clústeres.
- **NLP Service**: Integración con un **Modelo NLP Local** (cuya implementación se realizará en una fase posterior). Recibirá el análisis matemático de riesgo y generará una recomendación operativa, táctica y en lenguaje natural (Directiva de Acción) para los brigadistas de forma offline y privada.

### 3. Tareas en Segundo Plano (Celery)
El módulo implementa un *worker* de **Celery** soportado por **Redis** como *Message Broker*.
- Tareas programadas periódicamente descargan datos meteorológicos de APIs externas (e.g., OpenWeather).
- Alimentan a los modelos matemáticos automáticamente en la base de datos para mantener actualizados los niveles de alerta por zona.

## Flujo de Trabajo (Inferencia)
1. **Entrada de Datos**: El servicio recibe un vector de variables meteorológicas (Temperatura, Humedad, Viento, Precipitación) correspondientes a una zona protegida.
2. **Clasificación**: Se ejecutan las predicciones cruzadas de *Isolation Forest* y *KMeans*.
3. **Traducción**: El modelo de lenguaje generativo redacta las acciones a tomar.
4. **Persistencia y Trazabilidad**: El resultado completo se almacena en `PrediccionRiesgo` (PostGIS) con un UUID único y sello de tiempo.
5. **Respuesta**: Se devuelve el payload consolidado al cliente o al Backend Operativo.

## Tecnologías Utilizadas
- **FastAPI**: Servidor web ASGI ultra rápido.
- **SQLAlchemy + GeoAlchemy2**: ORM y extensiones espaciales.
- **PostGIS**: Base de datos geoespacial.
- **Celery + Redis**: Gestión de colas y tareas asíncronas.
- **Scikit-Learn / Pandas**: Procesamiento y algoritmos de Machine Learning Clásico.
- **Modelos Locales de NLP**: Modelado del Lenguaje Natural para reportes (Fase Futura).
- **Docker + Docker Compose**: Orquestación e isolación de contenedores.
