-- ==============================================================================
-- Esquema de Base de Datos Espacial para PyroGuard AI
-- Base de Datos: PostgreSQL + PostGIS
-- ==============================================================================

-- 1. Habilitar las extensiones necesarias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Creación de la Tabla: Zonas_Protegidas
CREATE TABLE Zonas_Protegidas (
    id_zona UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre VARCHAR(255) UNIQUE NOT NULL,
    geometria GEOMETRY(POLYGON, 4326) NOT NULL,
    area_hectareas DOUBLE PRECISION
);

-- Crear un índice espacial para acelerar las consultas sobre los polígonos
CREATE INDEX idx_zonas_protegidas_geom ON Zonas_Protegidas USING GIST (geometria);

-- 3. Creación de la Tabla: Condiciones_Meteorologicas
CREATE TABLE Condiciones_Meteorologicas (
    id_condicion UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_zona UUID REFERENCES Zonas_Protegidas(id_zona) ON DELETE CASCADE,
    fecha_hora TIMESTAMP NOT NULL,
    temperatura DOUBLE PRECISION,
    humedad DOUBLE PRECISION,
    viento DOUBLE PRECISION,
    precipitacion DOUBLE PRECISION
);

-- Crear índice sobre la fecha para acelerar búsquedas de series de tiempo
CREATE INDEX idx_condiciones_fecha ON Condiciones_Meteorologicas(fecha_hora);

-- 4. Creación de la Tabla: Incidentes_Historicos
CREATE TABLE Incidentes_Historicos (
    id_incidente UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_zona UUID REFERENCES Zonas_Protegidas(id_zona) ON DELETE CASCADE,
    fecha_deteccion TIMESTAMP NOT NULL,
    fuente VARCHAR(50) NOT NULL CHECK (fuente IN ('FIRMS', 'CONAFOR')),
    coordenada GEOMETRY(POINT, 4326) NOT NULL
);

-- Índice espacial para los puntos de incendio y otro para la fecha
CREATE INDEX idx_incidentes_geom ON Incidentes_Historicos USING GIST (coordenada);
CREATE INDEX idx_incidentes_fecha ON Incidentes_Historicos(fecha_deteccion);

-- 5. Creación de la Tabla: Predicciones_Riesgo (Historial de Inferencias del ML)
CREATE TABLE Predicciones_Riesgo (
    id_prediccion UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_zona UUID REFERENCES Zonas_Protegidas(id_zona) ON DELETE SET NULL,
    fecha_evaluacion TIMESTAMP NOT NULL DEFAULT NOW(),
    nivel_riesgo VARCHAR(50) NOT NULL CHECK (nivel_riesgo IN ('Bajo', 'Medio', 'Alto', 'Crítico')),
    resultados_json JSONB,
    directiva_nlp TEXT
);

-- Índice sobre la fecha y zona para consultar historiales rápidamente
CREATE INDEX idx_predicciones_fecha ON Predicciones_Riesgo(fecha_evaluacion);
CREATE INDEX idx_predicciones_zona ON Predicciones_Riesgo(id_zona);

-- ==============================================================================
-- FIN DEL ESQUEMA
-- ==============================================================================
