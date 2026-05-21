-- ============================================================
-- queries_analyze.sql — NYC Taxi Data Warehouse
-- Consultas utilizadas para EXPLAIN ANALYZE
-- ============================================================

-- ============================================================
-- CONSULTA 1 — Partition Pruning
-- Demuestra que PostgreSQL solo escanea la partición de enero 2025
-- cuando se aplica un filtro de fecha específico
-- ============================================================

EXPLAIN ANALYZE
SELECT COUNT(*), AVG(total_amount)
FROM fact_viajes
WHERE pickup_datetime >= '2025-01-01'
AND pickup_datetime < '2025-02-01';

-- ============================================================
-- CONSULTA 2 — Índice en zona_pickup_id (JOIN con dim_zona)
-- Motiva: idx_fact_viajes_zona_pickup
-- Pregunta de negocio: ¿Cuántos viajes salieron de cada zona
-- de Manhattan y cuál fue el ingreso promedio?
-- ============================================================

EXPLAIN ANALYZE
SELECT dz.zone, COUNT(*) AS viajes, AVG(fv.total_amount) AS ingreso_promedio
FROM fact_viajes fv
JOIN dim_zona dz ON fv.zona_pickup_id = dz.zona_id
WHERE dz.borough = 'Manhattan'
GROUP BY dz.zone
ORDER BY viajes DESC;

-- ============================================================
-- CONSULTA 3 — Índice compuesto (pickup_datetime + zona_pickup_id)
-- Motiva: idx_fact_viajes_pickup_zona
-- Pregunta de negocio: ¿Cuántos viajes y cuánto dinero se generó
-- en junio 2025 desde zonas de Manhattan?
-- ============================================================

EXPLAIN ANALYZE
SELECT COUNT(*), SUM(total_amount)
FROM fact_viajes
WHERE pickup_datetime >= '2025-06-01'
AND pickup_datetime < '2025-07-01'
AND zona_pickup_id IN (
    SELECT zona_id FROM dim_zona WHERE borough = 'Manhattan'
);

-- ============================================================
-- CONSULTA 4 — Índice en tiempo_id (JOIN con dim_tiempo)
-- Motiva: idx_fact_viajes_tiempo
-- Pregunta de negocio: ¿Cuál es el ingreso promedio por día
-- de la semana durante todo el año?
-- ============================================================

EXPLAIN ANALYZE
SELECT dt.dia_semana, COUNT(*) AS viajes, AVG(fv.total_amount) AS ingreso_promedio
FROM fact_viajes fv
JOIN dim_tiempo dt ON fv.tiempo_id = dt.tiempo_id
GROUP BY dt.dia_semana
ORDER BY ingreso_promedio DESC;

-- ============================================================
-- CONSULTA 5 — Índice en id_metodo_pago
-- Motiva: idx_fact_viajes_metodo_pago
-- Pregunta de negocio: ¿Cuánto se recaudó por tipo de pago?
-- ============================================================

EXPLAIN ANALYZE
SELECT dmp.payment_descripcion, COUNT(*) AS viajes, SUM(fv.total_amount) AS total_recaudado
FROM fact_viajes fv
JOIN dim_metodo_pago dmp ON fv.id_metodo_pago = dmp.id_metodo_pago
GROUP BY dmp.payment_descripcion
ORDER BY total_recaudado DESC;
