-- Índices de rendimiento para la bandeja de técnicos y la búsqueda de texto.

-- Búsqueda parcial (ILIKE '%texto%') con trigramas
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Bandeja del técnico: igualdad en assigned_to y status, orden por fecha
CREATE INDEX IF NOT EXISTS idx_tickets_assigned_status_created
    ON tickets (assigned_to, status, created_at DESC);

-- Búsqueda de texto en título y descripción
CREATE INDEX IF NOT EXISTS idx_tickets_title_trgm
    ON tickets USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_tickets_description_trgm
    ON tickets USING gin (description gin_trgm_ops);

ANALYZE tickets;

