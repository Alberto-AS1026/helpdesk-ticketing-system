-- Datos de volumen para pruebas de rendimiento (solo desarrollo).
-- Repetible: borra primero los tickets BULK- anteriores.

DELETE FROM tickets WHERE title LIKE 'BULK-%';

WITH
  p AS (SELECT array_agg(id) AS a FROM priorities),
  c AS (SELECT array_agg(id) AS a FROM categories),
  u AS (SELECT array_agg(id) AS a FROM users WHERE role = 'user' AND is_active),
  t AS (SELECT array_agg(id) AS a FROM technicians WHERE is_active)
INSERT INTO tickets
    (title, description, status, priority_id, category_id, created_by, assigned_to, created_at)
SELECT
    'BULK-' || g || ' ' ||
      (ARRAY['Wifi lenta','Impresora atascada','Equipo no arranca',
             'Error de VPN','Contraseña caducada','Pantalla parpadea'])[1 + floor(random() * 6)::int],
    'Ticket generado para pruebas de rendimiento número ' || g,
    (ARRAY['Abierto','En progreso','Pendiente','Resuelto','Cerrado'])[1 + floor(random() * 5)::int],
    p.a[1 + floor(random() * cardinality(p.a))::int],
    c.a[1 + floor(random() * cardinality(c.a))::int],
    u.a[1 + floor(random() * cardinality(u.a))::int],
    CASE WHEN random() < 0.3 THEN NULL
         ELSE t.a[1 + floor(random() * cardinality(t.a))::int] END,
    now() - random() * interval '180 days'
FROM generate_series(1, 50000) AS g, p, c, u, t;

-- Tiempos de resolución coherentes para los tickets resueltos o cerrados
UPDATE tickets
SET resolution_minutes = 5 + floor(random() * 4000)::int
WHERE title LIKE 'BULK-%' AND status IN ('Resuelto', 'Cerrado');

UPDATE tickets
SET resolved_at = created_at + resolution_minutes * interval '1 minute'
WHERE title LIKE 'BULK-%' AND resolution_minutes IS NOT NULL;

-- Actualiza las estadísticas que usa el planificador
ANALYZE tickets;
