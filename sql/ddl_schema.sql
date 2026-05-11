-- ============================================================
-- DDL Schema — NYC Taxi Data Warehouse
-- Proyecto: NYC Taxi Trip Records
-- Modelo: Esquema Estrella
-- Base de datos: nyc_taxi_dw

-- ============================================================
-- DIMENSIONES
-- ============================================================

-- 1. dim_tiempo
-- Contiene la información temporal derivada de tpep_pickup_datetime
CREATE TABLE IF NOT EXISTS dim_tiempo (
    tiempo_id        INT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha            DATE         NOT NULL,
    dia              SMALLINT     NOT NULL,
    mes              SMALLINT     NOT NULL,
    trimestre        SMALLINT     NOT NULL,
    anio             SMALLINT     NOT NULL,
    dia_semana       VARCHAR(10)  NOT NULL,
    es_fin_de_semana BOOLEAN      NOT NULL
);

-- 2. dim_zona
-- Contiene la información geográfica de las zonas de taxi de NYC
-- Actúa como dimensión de rol: se usa dos veces en fact_viajes
-- (zona_pickup_id y zona_dropoff_id)
CREATE TABLE IF NOT EXISTS dim_zona (
    zona_id     INT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id INT          NOT NULL,
    zone        VARCHAR(60)  NOT NULL,
    borough     VARCHAR(30)  NOT NULL,
    shape_area  FLOAT,
    shape_leng  FLOAT
);

-- 3. dim_proveedor
-- Contiene información sobre el proveedor TPEP del servicio de taxi
--Taxicab Passenger Enhancement Program(TPEP)
CREATE TABLE IF NOT EXISTS dim_proveedor (
    proveedor_id        INT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vendor_id           SMALLINT     NOT NULL,
    vendor_nombre       VARCHAR(50)  NOT NULL,
    store_and_fwd_flag  CHAR(1),
    tipo_almacenamiento VARCHAR(35)
);

-- 4. dim_metodo_pago
-- Contiene los tipos de pago disponibles para los viajes
CREATE TABLE IF NOT EXISTS dim_metodo_pago (
    id_metodo_pago      INT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_type        VARCHAR(10)  NOT NULL,
    payment_descripcion VARCHAR(30)  NOT NULL
);

-- 5. dim_tarifa_pago
-- Contiene los tipos de tarifa aplicables a los viajes
CREATE TABLE IF NOT EXISTS dim_tarifa_pago (
    ratecode_id          INT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ratecode_descripcion VARCHAR(40)  NOT NULL
);

-- ============================================================
-- TABLA DE HECHOS CON PARTICIONAMIENTO
-- ============================================================

-- fact_viajes se particiona por rango de pickup_datetime (por mes)
-- Razón: con ~48.7M filas anuales, particionar por mes permite que
-- PostgreSQL lea solo la partición correspondiente al período
-- consultado, en vez de escanear toda la tabla.

CREATE TABLE IF NOT EXISTS fact_viajes (
    viaje_id              BIGINT    GENERATED ALWAYS AS IDENTITY,
    tiempo_id             INT       NOT NULL REFERENCES dim_tiempo(tiempo_id),
    zona_pickup_id        INT       NOT NULL REFERENCES dim_zona(zona_id),
    zona_dropoff_id       INT       NOT NULL REFERENCES dim_zona(zona_id),
    id_metodo_pago        INT       NOT NULL REFERENCES dim_metodo_pago(id_metodo_pago),
    proveedor_id          INT       NOT NULL REFERENCES dim_proveedor(proveedor_id),
    ratecode_id           INT       NOT NULL REFERENCES dim_tarifa_pago(ratecode_id),
    pickup_datetime       TIMESTAMP NOT NULL,
    dropoff_datetime      TIMESTAMP NOT NULL,
    passenger_count       INTEGER,
    trip_distance         FLOAT,
    fare_amount           FLOAT,
    extra                 FLOAT,
    mta_tax               FLOAT,
    tip_amount            FLOAT,
    tolls_amount          FLOAT,
    improvement_surcharge FLOAT,
    congestion_surcharge  FLOAT,
    airport_fee           FLOAT,
    cbd_congestion_fee    FLOAT,
    total_amount          FLOAT,
    PRIMARY KEY (viaje_id, pickup_datetime)
) PARTITION BY RANGE (pickup_datetime);

-- Particiones por mes — año 2025
CREATE TABLE IF NOT EXISTS fact_viajes_2025_01
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_02
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_03
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_04
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_05
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_06
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_07
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_08
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_09
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_10
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_11
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS fact_viajes_2025_12
    PARTITION OF fact_viajes
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- ============================================================
-- INDICES
-- ============================================================

-- Índice en pickup_datetime para filtrar por fecha y hora
-- Razón: la mayoría de consultas del dashboard filtran por período
CREATE INDEX IF NOT EXISTS idx_fact_viajes_pickup_datetime
    ON fact_viajes (pickup_datetime);

-- Índice en zona_pickup_id para filtrar por zona de recogida
-- Razón: preguntas como "¿cuántos viajes salieron de Manhattan?"
CREATE INDEX IF NOT EXISTS idx_fact_viajes_zona_pickup
    ON fact_viajes (zona_pickup_id);

-- Índice en zona_dropoff_id para filtrar por zona de entrega
-- Razón: preguntas como "¿cuántos viajes llegaron al JFK?"
CREATE INDEX IF NOT EXISTS idx_fact_viajes_zona_dropoff
    ON fact_viajes (zona_dropoff_id);

-- Índice en id_metodo_pago para filtrar por tipo de pago
-- Razón: preguntas como "¿cuánto se recaudó en pagos con tarjeta?"
CREATE INDEX IF NOT EXISTS idx_fact_viajes_metodo_pago
    ON fact_viajes (id_metodo_pago);

-- Índice en proveedor_id para filtrar por proveedor
-- Razón: preguntas como "¿qué proveedor genera más viajes?"
CREATE INDEX IF NOT EXISTS idx_fact_viajes_proveedor
    ON fact_viajes (proveedor_id);

-- Índice en tiempo_id para los JOINs con dim_tiempo
-- Razón: acelera la unión entre fact_viajes y dim_tiempo
CREATE INDEX IF NOT EXISTS idx_fact_viajes_tiempo
    ON fact_viajes (tiempo_id);

-- ============================================================
-- DATOS DE REFERENCIA (catálogos)
-- ============================================================

-- Poblar dim_metodo_pago con los códigos conocidos
INSERT INTO dim_metodo_pago (payment_type, payment_descripcion) VALUES
    ('0', 'Tarifa flexible'),
    ('1', 'Tarjeta de credito'),
    ('2', 'Efectivo'),
    ('3', 'Sin cargo'),
    ('4', 'Disputa'),
    ('5', 'Desconocido'),
    ('6', 'Viaje anulado');

-- Poblar dim_tarifa_pago con los códigos conocidos
INSERT INTO dim_tarifa_pago (ratecode_descripcion) VALUES
    ('Tarifa estandar'),
    ('JFK: tarifa fija'),
    ('Newark: tarifa especial'),
    ('Nassau o Westchester'),
    ('Tarifa negociada'),
    ('Viaje en grupo'),
    ('Desconocido');

-- Poblar dim_proveedor con los proveedores conocidos
INSERT INTO dim_proveedor (vendor_id, vendor_nombre, store_and_fwd_flag, tipo_almacenamiento) VALUES
    (1, 'Creative Mobile Technologies LLC', 'Y', 'Viaje almacenado y reenviado'),
    (1, 'Creative Mobile Technologies LLC', 'N', 'Envio directo en tiempo real'),
    (2, 'Curb Mobility LLC',               'Y', 'Viaje almacenado y reenviado'),
    (2, 'Curb Mobility LLC',               'N', 'Envio directo en tiempo real'),
    (6, 'Myle Technologies Inc',           'Y', 'Viaje almacenado y reenviado'),
    (6, 'Myle Technologies Inc',           'N', 'Envio directo en tiempo real'),
    (7, 'Helix',                           'Y', 'Viaje almacenado y reenviado'),
    (7, 'Helix',                           'N', 'Envio directo en tiempo real');
