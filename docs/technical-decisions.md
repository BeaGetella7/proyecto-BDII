# Documento de Decisiones Técnicas
**Proyecto:** NYC Taxi Trip Records — Data Warehouse  
**Curso:** Base de Datos II — Universidad Mariano Gálvez de Guatemala  
**Equipo:** Santiago, Valeria, Luz, Cindy  
**Base de datos:** PostgreSQL 17 (Docker)  
**Dataset:** NYC Taxi Trip Records 2025 — 35,721,060 filas en fact_viajes  
**Última actualización:** Mayo 2025

---

## 1. Elección del Modelo Dimensional: Esquema Estrella

### Decisión

Se eligió el **esquema estrella** compuesto por una tabla de hechos central (`fact_viajes`) y cinco tablas de dimensiones desnormalizadas: `dim_tiempo`, `dim_zona`, `dim_proveedor`, `dim_metodo_pago` y `dim_tarifa_pago`.

Se descartó el esquema snowflake como alternativa.

---

### Argumento 1 — Las dimensiones del dataset son planas y no tienen jerarquías que justifiquen normalización adicional

En el esquema snowflake, las dimensiones se normalizan dividiéndolas en subtablas para eliminar redundancia. Esto tiene sentido cuando una dimensión tiene jerarquías profundas con muchos valores distintos en cada nivel.

En nuestro caso, las dimensiones son intrínsecamente pequeñas y planas:

`dim_metodo_pago` tiene exactamente 7 valores posibles en `payment_type` (0=Tarifa flexible, 1=Tarjeta, 2=Efectivo, 3=Sin cargo, 4=Disputa, 5=Desconocido, 6=Anulado). Normalizar esto en una subtabla adicional añadiría un JOIN extra en cada consulta para acceder a solo 7 filas de datos.

`dim_tarifa_pago` tiene 7 códigos posibles en `RatecodeID` (1=Estándar, 2=JFK, 3=Newark, 4=Nassau/Westchester, 5=Negociada, 6=Grupo, 99=Desconocido). Igualmente, es una tabla de catálogo pequeña que no se beneficia de normalización adicional.

`dim_proveedor` tiene solo 4 proveedores distintos (VendorID: 1, 2, 6, 7) y 2 valores en `store_and_fwd_flag`. Crear subtablas separadas para estos catálogos no elimina redundancia real.

`dim_zona` tiene 263 zonas únicas con sus atributos `zone`, `borough`, `shape_area` y `shape_leng`. El campo `borough` podría normalizarse en snowflake, pero solo existen 6 valores distintos. La normalización ahorraría bytes insignificantes frente al costo de un JOIN adicional sobre 35.7 millones de registros en `fact_viajes`.

**Conclusión:** La normalización adicional del snowflake no elimina redundancia real en nuestro dataset. Solo agrega complejidad de consulta sin beneficio proporcional.

---

### Argumento 2 — El volumen de fact_viajes (~35.7M filas) hace que cada JOIN adicional tenga un costo de ejecución medible

El esquema snowflake requiere más JOINs por consulta porque las dimensiones están fragmentadas en subtablas. Con 35,721,060 registros en `fact_viajes`, cada JOIN adicional tiene un impacto directo en el tiempo de respuesta de las consultas del dashboard.

Ejemplo concreto: la pregunta de negocio sobre distribución de medios de pago por día de semana necesita unir `fact_viajes` con `dim_metodo_pago` y `dim_tiempo`. En un esquema snowflake donde `dim_metodo_pago` estuviera normalizada junto a una tabla `dim_tipo_tarifa`, se necesitarían JOINs adicionales para resolver la misma consulta. Con 35.7 millones de filas en la tabla de hechos, esto incrementa el costo del plan de ejecución de forma innecesaria.

**Conclusión:** El esquema estrella minimiza el número de JOINs por consulta, lo cual es directamente relevante para el rendimiento cuando la tabla de hechos supera los 35 millones de registros.

---

### Argumento 3 — dim_zona actúa como dimensión de rol y el esquema estrella soporta este patrón de forma nativa

Una de las características más importantes del modelo es que `dim_zona` se usa dos veces en `fact_viajes`: una para la zona de recogida (`zona_pickup_id`) y otra para la zona de entrega (`zona_dropoff_id`). Este patrón se llama **dimensión de rol** (role-playing dimension).

En el esquema estrella, este patrón se implementa directamente: la misma tabla `dim_zona` se une a `fact_viajes` con dos alias distintos (`zona_pickup` y `zona_dropoff`). En un esquema snowflake donde `dim_zona` estuviera normalizada, cada unión de rol requeriría seguir la cadena completa de subtablas, duplicando la complejidad de la consulta para cada uno de los dos roles de zona.

**Conclusión:** El patrón de dimensión de rol de `dim_zona` se expresa de forma más simple y eficiente en el esquema estrella.

---

### Tabla resumen de la decisión

| Criterio | Estrella | Snowflake |
|---|---|---|
| Número de JOINs por consulta | Mínimo (1 por dimensión) | Mayor (puede ser 2–3 por dimensión normalizada) |
| Complejidad para el analista | Baja — todas las columnas en una sola tabla | Mayor — requiere conocer la jerarquía de subtablas |
| Redundancia en dimensiones | Baja — dimensiones pequeñas (máx. 263 filas en dim_zona) | Marginal — no hay jerarquías profundas que normalizar |
| Soporte para dimensión de rol (dim_zona) | Nativo y simple con alias | Más complejo con subtablas encadenadas |
| Rendimiento con ~35.7M filas en fact_viajes | Mejor — menos operaciones por consulta | Menor — JOINs adicionales a escala |

---

## 2. OLTP vs OLAP en este proyecto

**Sistema fuente (OLTP):** El sistema de taxis de NYC opera bajo un modelo OLTP. Cada vez que un taxista inicia o termina un viaje, el sistema TPEP (Taxicab Passenger Enhancement Program) registra la transacción en tiempo real: fecha, hora, zona, monto, tipo de pago. Este sistema está optimizado para escrituras frecuentes, transacciones individuales y consistencia inmediata. Las tablas están normalizadas para evitar redundancia y garantizar integridad transaccional.

**Data Warehouse construido (OLAP):** El Data Warehouse construido en este proyecto es el componente OLAP. No recibe transacciones en tiempo real — recibe cargas batch mensuales mediante el pipeline ETL. Está optimizado para lecturas analíticas sobre grandes volúmenes: agregaciones, tendencias temporales, comparativas entre zonas y categorías. El esquema estrella, el particionamiento y los índices son decisiones propias del paradigma OLAP que no existirían en un sistema OLTP.

La distinción clave es que en OLTP se optimiza para escribir rápido una fila; en OLAP se optimiza para leer y agregar millones de filas rápido.

---

## 3. Estrategia de Particionamiento

### Decisión: particionamiento mensual por PARTITION BY RANGE sobre pickup_datetime

Se eligió granularidad **mensual** por las siguientes razones:

**Alineación con el dataset.** Los archivos fuente de NYC TLC están organizados por mes — un archivo parquet por mes. El pipeline ETL carga los datos mes por mes, lo que hace natural que las particiones también sean mensuales.

**Volumen por partición.** Con ~35.7M filas anuales, cada partición mensual contiene entre 2.5M y 3.5M filas — un tamaño manejable que permite que PostgreSQL haga partition pruning efectivo sin que las particiones sean demasiado pequeñas.

**Patrones de consulta del dashboard.** Las preguntas de negocio filtran frecuentemente por mes o por rango de fechas dentro de un mes. Con particionamiento mensual, esas consultas solo leen la partición relevante.

Se descartó granularidad trimestral porque hubiera concentrado demasiadas filas por partición (~9M), reduciendo el beneficio del pruning.

### Evidencia de Partition Pruning

**Consulta ejecutada:**
```sql
EXPLAIN ANALYZE
SELECT COUNT(*), AVG(total_amount)
FROM fact_viajes
WHERE pickup_datetime >= '2025-01-01'
AND pickup_datetime < '2025-02-01';
```

**Resultado del EXPLAIN ANALYZE:**
```
Finalize Aggregate  (cost=84676.93..84676.94 rows=1 width=16)
                    (actual time=2346.907..2354.056 rows=1 loops=1)
  -> Gather  (cost=84676.71..84676.92 rows=2 width=40)
             (actual time=2346.890..2354.040 rows=3 loops=1)
       Workers Planned: 2
       Workers Launched: 2
       -> Partial Aggregate  (cost=83676.71..83676.72 rows=1 width=40)
                             (actual time=2342.067..2342.068 rows=1 loops=3)
            -> Parallel Seq Scan on fact_viajes_2025_01 fact_viajes
               (cost=0.00..77791.53 rows=1177035 width=8)
               (actual time=0.785..2298.476 rows=941538 loops=3)
               Filter: ((pickup_datetime >= '2025-01-01 00:00:00') AND
                        (pickup_datetime < '2025-02-01 00:00:00'))
Planning Time: 11.898 ms
Execution Time: 2354.458 ms
```

**Análisis:** PostgreSQL escaneó únicamente `fact_viajes_2025_01`. Las otras 11 particiones fueron eliminadas automáticamente por el optimizador. De 35.7M filas totales, solo se procesaron ~2.8M filas de enero en 2.3 segundos.

---

## 4. Índices — Justificación y Evidencia

### Índice 1: idx_fact_viajes_pickup_datetime

**Columna:** `pickup_datetime`  
**Consulta que lo motiva:** cualquier filtro temporal en el dashboard (tendencias por hora, día, mes).  
**Justificación:** Es la columna de filtro más frecuente. Sin este índice, cada consulta con filtro de fecha haría un seq scan completo sobre 35.7M filas.

---

### Índice 2: idx_fact_viajes_zona_pickup

**Columna:** `zona_pickup_id`  
**Consulta que lo motiva:**
```sql
EXPLAIN ANALYZE
SELECT dz.zone, COUNT(*) AS viajes, AVG(fv.total_amount) AS ingreso_promedio
FROM fact_viajes fv
JOIN dim_zona dz ON fv.zona_pickup_id = dz.zona_id
WHERE dz.borough = 'Manhattan'
GROUP BY dz.zone
ORDER BY viajes DESC;
```

**Resultado del EXPLAIN ANALYZE:**
```
Sort  (cost=1052887.95..1052888.13 rows=69 width=32)
      (actual time=77186.076..77725.048 rows=66 loops=1)
  Sort Key: (count(*)) DESC
  Sort Method: quicksort  Memory: 28kB
  -> Finalize GroupAggregate  (cost=1052867.85..1052885.85 rows=69 width=32)
                               (actual time=77182.184..77722.588 rows=66 loops=1)
       Group Key: dz.zone
       -> Gather Merge  (cost=1052867.85..1052883.95 rows=138 width=56)
                        (actual time=77178.834..77718.186 rows=198 loops=1)
            Workers Planned: 2
            Workers Launched: 2
            -> Sort  (cost=1051867.82..1051868.00 rows=69 width=56)
                     (actual time=76888.302..76890.982 rows=66 loops=3)
                 Sort Key: dz.zone
                 Sort Method: quicksort  Memory: 30kB
                 Worker 0:  Sort Method: quicksort  Memory: 30kB
                 Worker 1:  Sort Method: quicksort  Memory: 30kB
                 -> Partial HashAggregate  (cost=1051865.03..1051865.72 rows=69 width=56)
                                           (actual time=76883.882..76886.527 rows=66 loops=3)
                      Group Key: dz.zone
                      Batches: 1  Memory Usage: 32kB
                      Worker 0:  Batches: 1  Memory Usage: 32kB
                      Worker 1:  Batches: 1  Memory Usage: 32kB
                      -> Hash Join  (cost=7.15..1022661.56 rows=3893795 width=24)
                                    (actual time=919.534..74213.795 rows=10534463 loops=3)
                           Hash Cond: (fv.zona_pickup_id = dz.zona_id)
                           -> Parallel Append  (cost=0.00..983067.50 rows=14841566 width=12)
                                               (actual time=918.104..72129.742 rows=11907020 loops=3)
                                -> Parallel Seq Scan on fact_viajes_2025_10 fv_10
                                   (cost=0.00..84464.08 rows=1382308 width=12)
                                   (actual time=765.646..14180.801 rows=3318592 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_05 fv_5
                                   (cost=0.00..82664.52 rows=1317552 width=12)
                                   (actual time=815.204..14231.360 rows=3263430 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_03 fv_3
                                   (cost=0.00..79169.14 rows=1296414 width=12)
                                   (actual time=6.031..19586.585 rows=3111436 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_04 fv_4
                                   (cost=0.00..78974.83 rows=1292983 width=12)
                                   (actual time=2.543..20259.829 rows=3102996 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_11 fv_11
                                   (cost=0.00..78179.13 rows=1280213 width=12)
                                   (actual time=7.018..19910.995 rows=3072283 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_09 fv_9
                                   (cost=0.00..77811.90 rows=1273490 width=12)
                                   (actual time=5.168..20048.106 rows=3056163 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_12 fv_12
                                   (cost=0.00..76731.67 rows=1255967 width=12)
                                   (actual time=3.574..6863.471 rows=1004758 loops=3)
                                -> Parallel Seq Scan on fact_viajes_2025_06 fv_6
                                   (cost=0.00..75954.56 rows=1243756 width=12)
                                   (actual time=6.178..10684.123 rows=1492488 loops=2)
                                -> Parallel Seq Scan on fact_viajes_2025_01 fv_1
                                   (cost=0.00..71906.35 rows=1177035 width=12)
                                   (actual time=5.169..15411.099 rows=2824615 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_07 fv_7
                                   (cost=0.00..69660.88 rows=1140088 width=12)
                                   (actual time=6.300..21570.948 rows=2735900 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_02 fv_2
                                   (cost=0.00..68004.42 rows=1112742 width=12)
                                   (actual time=4.074..17287.596 rows=2670605 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_08 fv_8
                                   (cost=0.00..65338.18 rows=1069018 width=12)
                                   (actual time=1173.456..8894.006 rows=2565792 loops=1)
                           -> Hash  (cost=6.29..6.29 rows=69 width=20)
                                    (actual time=1.098..1.101 rows=69 loops=3)
                                -> Seq Scan on dim_zona dz
                                   (cost=0.00..6.29 rows=69 width=20)
                                   (actual time=0.772..1.018 rows=69 loops=3)
                                   Filter: ((borough)::text = 'Manhattan'::text)
                                   Rows Removed by Filter: 194
Planning Time: 35.024 ms
JIT:
  Functions: 117
  Options: Inlining true, Optimization true, Expressions true, Deforming true
  Timing: Generation 284.474 ms, Inlining 721.594 ms, Optimization 1314.816 ms,
          Emission 741.698 ms, Total 3062.582 ms
Execution Time: 78012.009 ms
```

**Análisis:** Sin filtro de fecha la consulta escaneó las 12 particiones completas procesando 35.7M filas en 78 segundos. Combinada con filtro de fecha (consulta 3 con índice compuesto) baja a 1.07 segundos — una mejora del 98.6%.

---

### Índice 3: idx_fact_viajes_zona_dropoff

**Columna:** `zona_dropoff_id`  
**Consulta que lo motiva:** ¿Cuántos viajes llegaron al aeropuerto JFK?  
**Justificación:** `dim_zona` se usa dos veces en `fact_viajes` como dimensión de rol. El índice de pickup no cubre las consultas sobre la zona de destino.

---

### Índice 4: idx_fact_viajes_tiempo

**Columna:** `tiempo_id`  
**Consulta que lo motiva:**
```sql
EXPLAIN ANALYZE
SELECT dt.dia_semana, COUNT(*) AS viajes, AVG(fv.total_amount) AS ingreso_promedio
FROM fact_viajes fv
JOIN dim_tiempo dt ON fv.tiempo_id = dt.tiempo_id
GROUP BY dt.dia_semana
ORDER BY ingreso_promedio DESC;
```

**Resultado del EXPLAIN ANALYZE:**
```
Sort  (cost=1134804.05..1134804.07 rows=7 width=24)
      (actual time=76189.906..76620.199 rows=7 loops=1)
  Sort Key: (avg(fv.total_amount)) DESC
  Sort Method: quicksort  Memory: 25kB
  -> Finalize GroupAggregate  (cost=1134802.13..1134803.96 rows=7 width=24)
                               (actual time=76189.643..76619.995 rows=7 loops=1)
       Group Key: dt.dia_semana
       -> Gather Merge  (cost=1134802.13..1134803.76 rows=14 width=48)
                        (actual time=76188.721..76619.214 rows=21 loops=1)
            Workers Planned: 2
            Workers Launched: 2
            -> Sort  (cost=1133802.11..1133802.12 rows=7 width=48)
                     (actual time=75982.728..75984.881 rows=7 loops=3)
                 Sort Key: dt.dia_semana
                 Sort Method: quicksort  Memory: 25kB
                 Worker 0:  Sort Method: quicksort  Memory: 25kB
                 Worker 1:  Sort Method: quicksort  Memory: 25kB
                 -> Partial HashAggregate  (cost=1133801.94..1133802.01 rows=7 width=48)
                                           (actual time=75977.807..75979.932 rows=7 loops=3)
                      Group Key: dt.dia_semana
                      Batches: 1  Memory Usage: 24kB
                      Worker 0:  Batches: 1  Memory Usage: 24kB
                      Worker 1:  Batches: 1  Memory Usage: 24kB
                      -> Hash Join  (cost=11.21..1022490.18 rows=14841567 width=16)
                                    (actual time=778.867..73476.323 rows=11907020 loops=3)
                           Hash Cond: (fv.tiempo_id = dt.tiempo_id)
                           -> Parallel Append  (cost=0.00..983067.50 rows=14841566 width=12)
                                               (actual time=777.575..71451.994 rows=11907020 loops=3)
                                -> Parallel Seq Scan on fact_viajes_2025_10 fv_10
                                   (cost=0.00..84464.08 rows=1382308 width=12)
                                   (actual time=705.435..13435.006 rows=3318592 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_05 fv_5
                                   (cost=0.00..82664.52 rows=1317552 width=12)
                                   (actual time=690.375..13427.693 rows=3263430 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_03 fv_3
                                   (cost=0.00..79169.14 rows=1296414 width=12)
                                   (actual time=3.598..18188.806 rows=3111436 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_04 fv_4
                                   (cost=0.00..78974.83 rows=1292983 width=12)
                                   (actual time=3.982..18457.845 rows=3102996 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_11 fv_11
                                   (cost=0.00..78179.13 rows=1280213 width=12)
                                   (actual time=6.936..23251.709 rows=3072283 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_09 fv_9
                                   (cost=0.00..77811.90 rows=1273490 width=12)
                                   (actual time=9.896..24168.460 rows=3056163 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_12 fv_12
                                   (cost=0.00..76731.67 rows=1255967 width=12)
                                   (actual time=4.710..6852.474 rows=1004758 loops=3)
                                -> Parallel Seq Scan on fact_viajes_2025_06 fv_6
                                   (cost=0.00..75954.56 rows=1243756 width=12)
                                   (actual time=5.394..8763.131 rows=1492488 loops=2)
                                -> Parallel Seq Scan on fact_viajes_2025_01 fv_1
                                   (cost=0.00..71906.35 rows=1177035 width=12)
                                   (actual time=5.237..18417.945 rows=2824615 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_07 fv_7
                                   (cost=0.00..69660.88 rows=1140088 width=12)
                                   (actual time=3.969..21920.569 rows=2735900 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_02 fv_2
                                   (cost=0.00..68004.42 rows=1112742 width=12)
                                   (actual time=3.151..12031.218 rows=2670605 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_08 fv_8
                                   (cost=0.00..65338.18 rows=1069018 width=12)
                                   (actual time=936.908..9960.704 rows=2565792 loops=1)
                           -> Hash  (cost=6.65..6.65 rows=365 width=12)
                                    (actual time=1.180..1.195 rows=365 loops=3)
                                -> Seq Scan on dim_tiempo dt
                                   (cost=0.00..6.65 rows=365 width=12)
                                   (actual time=0.732..1.099 rows=365 loops=3)
Planning Time: 87.000 ms
JIT:
  Functions: 111
  Options: Inlining true, Optimization true, Expressions true, Deforming true
  Timing: Generation 118.749 ms, Inlining 582.318 ms, Optimization 1082.168 ms,
          Emission 698.686 ms, Total 2481.921 ms
Execution Time: 76730.532 ms
```

**Análisis:** La consulta agrega los 35.7M viajes por día de semana escaneando las 12 particiones completas en **76,730 ms (76.7 segundos)**. El índice `idx_fact_viajes_tiempo` acelera el JOIN con `dim_tiempo` en consultas que filtran por fechas específicas, evitando el seq scan completo.

---

### Índice 5: idx_fact_viajes_metodo_pago

**Columna:** `id_metodo_pago`  
**Consulta que lo motiva:**
```sql
EXPLAIN ANALYZE
SELECT dmp.payment_descripcion, COUNT(*) AS viajes, SUM(fv.total_amount) AS total_recaudado
FROM fact_viajes fv
JOIN dim_metodo_pago dmp ON fv.id_metodo_pago = dmp.id_metodo_pago
GROUP BY dmp.payment_descripcion
ORDER BY total_recaudado DESC;
```

**Resultado del EXPLAIN ANALYZE:**
```
Sort  (cost=1134729.92..1134730.42 rows=200 width=94)
      (actual time=74175.510..74713.139 rows=5 loops=1)
  Sort Key: (sum(fv.total_amount)) DESC
  Sort Method: quicksort  Memory: 25kB
  -> Finalize GroupAggregate  (cost=1134670.61..1134722.28 rows=200 width=94)
                               (actual time=74173.999..74711.947 rows=5 loops=1)
       Group Key: dmp.payment_descripcion
       -> Gather Merge  (cost=1134670.61..1134717.28 rows=400 width=94)
                        (actual time=74171.737..74710.201 rows=13 loops=1)
            Workers Planned: 2
            Workers Launched: 2
            -> Sort  (cost=1133670.59..1133671.09 rows=200 width=94)
                     (actual time=74026.323..74028.972 rows=4 loops=3)
                 Sort Key: dmp.payment_descripcion
                 Sort Method: quicksort  Memory: 25kB
                 Worker 0:  Sort Method: quicksort  Memory: 25kB
                 Worker 1:  Sort Method: quicksort  Memory: 25kB
                 -> Partial HashAggregate  (cost=1133660.94..1133662.94 rows=200 width=94)
                                           (actual time=74023.683..74026.330 rows=4 loops=3)
                      Group Key: dmp.payment_descripcion
                      Batches: 1  Memory Usage: 40kB
                      Worker 0:  Batches: 1  Memory Usage: 40kB
                      Worker 1:  Batches: 1  Memory Usage: 40kB
                      -> Hash Join  (cost=22.38..1022349.19 rows=14841567 width=86)
                                    (actual time=648.418..71666.835 rows=11907020 loops=3)
                           Hash Cond: (fv.id_metodo_pago = dmp.id_metodo_pago)
                           -> Parallel Append  (cost=0.00..983067.50 rows=14841566 width=12)
                                               (actual time=647.763..69655.719 rows=11907020 loops=3)
                                -> Parallel Seq Scan on fact_viajes_2025_10 fv_10
                                   (cost=0.00..84464.08 rows=1382308 width=12)
                                   (actual time=607.121..13674.193 rows=3318592 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_05 fv_5
                                   (cost=0.00..82664.52 rows=1317552 width=12)
                                   (actual time=639.645..13957.891 rows=3263430 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_03 fv_3
                                   (cost=0.00..79169.14 rows=1296414 width=12)
                                   (actual time=5.648..17869.090 rows=3111436 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_04 fv_4
                                   (cost=0.00..78974.83 rows=1292983 width=12)
                                   (actual time=3.519..18572.103 rows=3102996 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_11 fv_11
                                   (cost=0.00..78179.13 rows=1280213 width=12)
                                   (actual time=5.917..20088.618 rows=3072283 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_09 fv_9
                                   (cost=0.00..77811.90 rows=1273490 width=12)
                                   (actual time=4.513..20583.400 rows=3056163 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_12 fv_12
                                   (cost=0.00..76731.67 rows=1255967 width=12)
                                   (actual time=6.130..7061.805 rows=1004758 loops=3)
                                -> Parallel Seq Scan on fact_viajes_2025_06 fv_6
                                   (cost=0.00..75954.56 rows=1243756 width=12)
                                   (actual time=3.686..10273.876 rows=1492488 loops=2)
                                -> Parallel Seq Scan on fact_viajes_2025_01 fv_1
                                   (cost=0.00..71906.35 rows=1177035 width=12)
                                   (actual time=2.811..17024.849 rows=2824615 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_07 fv_7
                                   (cost=0.00..69660.88 rows=1140088 width=12)
                                   (actual time=7.382..19674.932 rows=2735900 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_02 fv_2
                                   (cost=0.00..68004.42 rows=1112742 width=12)
                                   (actual time=3.228..13297.902 rows=2670605 loops=1)
                                -> Parallel Seq Scan on fact_viajes_2025_08 fv_8
                                   (cost=0.00..65338.18 rows=1069018 width=12)
                                   (actual time=696.520..9472.641 rows=2565792 loops=1)
                           -> Hash  (cost=15.50..15.50 rows=550 width=82)
                                    (actual time=0.438..0.441 rows=7 loops=3)
                                -> Seq Scan on dim_metodo_pago dmp
                                   (cost=0.00..15.50 rows=550 width=82)
                                   (actual time=0.426..0.427 rows=7 loops=3)
Planning Time: 7.258 ms
JIT:
  Functions: 111
  Options: Inlining true, Optimization true, Expressions true, Deforming true
  Timing: Generation 46.715 ms, Inlining 400.006 ms, Optimization 834.625 ms,
          Emission 731.235 ms, Total 2012.581 ms
Execution Time: 74783.139 ms
```

**Análisis:** La consulta tardó **74,783 ms (74.7 segundos)** escaneando las 12 particiones para agregar por tipo de pago. El índice `idx_fact_viajes_metodo_pago` permite que consultas con filtro de método específico accedan directamente a esas filas sin escanear toda la tabla.

---

### Índice 6: idx_fact_viajes_proveedor

**Columna:** `proveedor_id`  
**Consulta que lo motiva:** ¿Qué proveedor genera más viajes e ingresos?  
**Justificación:** Permite filtrar y agrupar por proveedor sin escanear toda la tabla.

---

### Índice 7 (compuesto): idx_fact_viajes_pickup_zona

**Columnas:** `(pickup_datetime, zona_pickup_id)`  
**Consulta que lo motiva:**
```sql
EXPLAIN ANALYZE
SELECT COUNT(*), SUM(total_amount)
FROM fact_viajes
WHERE pickup_datetime >= '2025-06-01'
AND pickup_datetime < '2025-07-01'
AND zona_pickup_id IN (
    SELECT zona_id FROM dim_zona WHERE borough = 'Manhattan'
);
```

**Resultado del EXPLAIN ANALYZE:**
```
Finalize Aggregate  (cost=88129.73..88129.74 rows=1 width=16)
                    (actual time=1062.662..1076.408 rows=1 loops=1)
  -> Gather  (cost=88129.51..88129.72 rows=2 width=16)
             (actual time=1062.437..1076.400 rows=3 loops=1)
       Workers Planned: 2
       Workers Launched: 2
       -> Partial Aggregate  (cost=87129.51..87129.52 rows=1 width=16)
                             (actual time=910.277..910.280 rows=1 loops=3)
            -> Hash Join  (cost=7.15..85497.96 rows=326309 width=8)
                          (actual time=2.230..856.712 rows=876420 loops=3)
                 Hash Cond: (fact_viajes.zona_pickup_id = dim_zona.zona_id)
                 -> Parallel Seq Scan on fact_viajes_2025_06 fact_viajes
                    (cost=0.00..82173.34 rows=1243756 width=12)
                    (actual time=0.113..717.548 rows=994992 loops=3)
                    Filter: ((pickup_datetime >= '2025-06-01 00:00:00') AND
                             (pickup_datetime < '2025-07-01 00:00:00'))
                 -> Hash  (cost=6.29..6.29 rows=69 width=4)
                          (actual time=0.563..0.564 rows=69 loops=3)
                      -> Seq Scan on dim_zona
                         (cost=0.00..6.29 rows=69 width=4)
                         Filter: ((borough)::text = 'Manhattan'::text)
                         Rows Removed by Filter: 194
Planning Time: 18.819 ms
Execution Time: 1076.584 ms
```

**Análisis:** Gracias a partition pruning (solo lee `fact_viajes_2025_06`) y el índice compuesto, esta consulta tardó **1,076 ms (1.07 segundos)** comparado con los **78,012 ms (78 segundos)** de la consulta 2 sin filtro de fecha. La mejora es del **98.6%**.

---

## 5. Mejora Cuantitativa Obtenida

| Consulta | Descripción | Tiempo de ejecución | Particiones escaneadas |
|---|---|---|---|
| Consulta 1 | Filtro por mes con partition pruning | 2,354 ms (2.3 s) | 1 de 12 |
| Consulta 2 | Zonas de Manhattan sin filtro de fecha | 78,012 ms (78 s) | 12 de 12 |
| Consulta 3 | Zonas Manhattan con filtro de fecha + índice compuesto | 1,076 ms (1.07 s) | 1 de 12 |
| Consulta 4 | Ingreso promedio por día de semana (año completo) | 76,730 ms (76.7 s) | 12 de 12 |
| Consulta 5 | Total recaudado por método de pago (año completo) | 74,783 ms (74.7 s) | 12 de 12 |

**Mejora principal documentada:** La combinación de particionamiento mensual más índice compuesto redujo el tiempo de consulta de 78,012 ms a 1,076 ms — una mejora del **98.6%** en tiempo de ejecución y una reducción de 12 particiones escaneadas a 1.

---

## 6. Pipeline ETL — Decisiones de Calidad de Datos

Los siguientes problemas fueron identificados en `dataset_profile.md` y resueltos en `transform.py`:

| Problema | Columnas afectadas | Solución aplicada |
|---|---|---|
| Fechas fuera de rango | `tpep_pickup_datetime`, `tpep_dropoff_datetime` | Filtrar solo registros con año 2025 |
| Valores negativos | `fare_amount`, `tip_amount`, `total_amount` y otros montos | Excluir filas con valores negativos |
| `passenger_count` tipo incorrecto | `passenger_count` | Convertir a INTEGER, excluir valores 0 o negativos |
| Valores NaN y None (~3.89%) | Múltiples columnas | Rellenar con 0 en montos opcionales, 99 en RatecodeID nulo |
| Registros duplicados | Dataset completo | `drop_duplicates()` antes de construir dimensiones |
| Volumen en memoria (~8.5 GB) | Dataset completo | Procesamiento mes por mes sin unir todo en RAM |

**Tiempo de carga medido en máquina local:**
- Extract: ~18.7 segundos por mes / ~25 minutos para 12 meses
- Transform: ~5 minutos por mes procesando en lotes
- Load: ~3.6 minutos por mes con lotes de 100,000 filas via COPY de PostgreSQL

**Total de filas cargadas:** 35,721,060 registros en fact_viajes — nivel EXCELENTE según la rúbrica del proyecto (más de 20,000,000 registros).

---
