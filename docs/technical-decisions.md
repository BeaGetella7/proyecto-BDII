# Documento de Decisiones Técnicas
**Proyecto:** NYC Taxi Trip Records — Data Warehouse  
**Curso:** Base de Datos II — Universidad Mariano Gálvez de Guatemala  
**Última actualización:** Abril 2025

---

## 1. Elección del Modelo Dimensional: Esquema Estrella

### Decisión

Se eligió el **esquema estrella** compuesto por una tabla de hechos central (`fact_viajes`) y cinco tablas de dimensiones desnormalizadas: `dim_tiempo`, `dim_zona`, `dim_proveedor`, `dim_metodo_pago` y `dim_tarifa_pago`.

Se descartó el **esquema snowflake** como alternativa.

---

### ¿Por qué estrella y no snowflake?

#### Argumento 1 — Las dimensiones del dataset son planas y no tienen jerarquías que justifiquen normalización adicional

En el esquema snowflake, las dimensiones se normalizan dividiéndolas en subtablas para eliminar redundancia. Esto tiene sentido cuando una dimensión tiene jerarquías profundas con muchos valores distintos en cada nivel.

En nuestro caso, las dimensiones son intrínsecamente pequeñas y planas:

- `dim_metodo_pago` tiene exactamente 7 valores posibles en `payment_type` (0=Tarifa flexible, 1=Tarjeta, 2=Efectivo, 3=Sin cargo, 4=Disputa, 5=Desconocido, 6=Anulado). Normalizar esto en una subtabla adicional añadiría un JOIN extra en cada consulta para acceder a solo 7 filas de datos. El costo de ejecución de ese JOIN supera con creces el beneficio de almacenamiento.

- `dim_tarifa_pago` tiene 7 códigos posibles en `RatecodeID` (1=Estándar, 2=JFK, 3=Newark, 4=Nassau/Westchester, 5=Negociada, 6=Grupo, 99=Desconocido). Igualmente, es una tabla de catálogo pequeña que no se beneficia de normalización adicional.

- `dim_proveedor` tiene solo 4 proveedores distintos (`VendorID`: 1, 2, 6, 7) y 2 valores en `store_and_fwd_flag`. Crear subtablas separadas para estos catálogos no elimina redundancia real.

- `dim_zona` tiene 263 zonas únicas con sus atributos `zone`, `borough`, `shape_area` y `shape_leng`. El campo `borough` podría normalizarse en una subtabla en un esquema snowflake, pero solo existen 6 valores distintos de borough (Manhattan, Brooklyn, Queens, Bronx, Staten Island, EWR). La normalización ahorraría bytes insignificantes frente al costo de un JOIN adicional sobre 48.7 millones de registros en `fact_viajes`.

**Conclusión:** La normalización adicional del snowflake no elimina redundancia real en nuestro dataset. Solo agrega complejidad de consulta sin beneficio proporcional.

---

#### Argumento 2 — El volumen de `fact_viajes` (~48.7M filas) hace que cada JOIN adicional tenga un costo de ejecución medible

El esquema snowflake requiere más JOINs por consulta porque las dimensiones están fragmentadas en subtablas. Con una tabla de hechos de aproximadamente 48.7 millones de registros anuales (promedio de 4,060,217 registros por mes según el perfil del dataset de Santiago), cada JOIN adicional tiene un impacto directo en el tiempo de respuesta de las consultas del dashboard.

El optimizador de PostgreSQL debe resolver más relaciones por consulta en un esquema snowflake. En consultas analíticas típicas del dashboard, por ejemplo ingresos por mes y zona o distribución de pago por día de semana, el esquema estrella permite al planificador acceder a todas las columnas de una dimensión en una sola lectura de tabla sin encadenar múltiples JOINs.

Ejemplo concreto con nuestro modelo: la pregunta de negocio 3 (distribución de medios de pago por día de semana) necesita unir `fact_viajes` con `dim_metodo_pago` y `dim_tiempo`. En un esquema snowflake donde `dim_metodo_pago` estuviera normalizada junto a una tabla `dim_tipo_tarifa`, se necesitarían JOINs adicionales para resolver la misma consulta. Con 48.7 millones de filas en la tabla de hechos, esto incrementa el costo del plan de ejecución de forma innecesaria.

**Conclusión:** El esquema estrella minimiza el número de JOINs por consulta, lo cual es directamente relevante para el rendimiento cuando la tabla de hechos supera los 48 millones de registros.

---

#### Argumento 3 — `dim_zona` actúa como dimensión de rol y el esquema estrella soporta este patrón de forma nativa

Una de las características más importantes de nuestro modelo es que `dim_zona` se usa dos veces en `fact_viajes`: una para la zona de recogida (`zona_pickup_id`) y otra para la zona de entrega (`zona_dropoff_id`). Este patrón se llama **dimensión de rol** (*role-playing dimension*).

En el esquema estrella, este patrón se implementa directamente: la misma tabla `dim_zona` se une a `fact_viajes` con dos alias distintos (`zona_pickup` y `zona_dropoff`). La consulta es legible y el planificador puede usar el mismo índice sobre `zona_id` para ambas uniones.

En un esquema snowflake donde `dim_zona` estuviera normalizada (por ejemplo separando `dim_borough` como subtabla independiente), cada unión de rol requeriría seguir la cadena completa de subtablas, duplicando la complejidad de la consulta para cada uno de los dos roles de zona.

Esto es especialmente relevante para la pregunta de negocio 2 del dashboard (zonas con mayor volumen de viajes y tarifa promedio), que necesita unir `fact_viajes` con `dim_zona` dos veces: una para la zona de origen y otra para la zona de destino.

**Conclusión:** El patrón de dimensión de rol de `dim_zona` se expresa de forma más simple y eficiente en el esquema estrella. El snowflake añadiría complejidad de consulta sin beneficio analítico.

---

### Tabla resumen de la decisión

| Criterio | Estrella | Snowflake |
|---|---|---|
| Número de JOINs por consulta | Mínimo (1 por dimensión) | Mayor (puede ser 2–3 por dimensión normalizada) |
| Complejidad para el analista | Baja — todas las columnas en una sola tabla | Mayor — requiere conocer la jerarquía de subtablas |
| Redundancia en dimensiones | Baja — dimensiones pequeñas (máx. 263 filas en `dim_zona`) | Marginal — no hay jerarquías profundas que normalizar |
| Soporte para dimensión de rol (`dim_zona`) | Nativo y simple con alias | Más complejo con subtablas encadenadas |
| Rendimiento con ~48.7M filas en `fact_viajes` | Mejor — menos operaciones por consulta | Menor — JOINs adicionales a escala |

---

## 2. Estrategia de Particionamiento

> *Esta sección se completará en las semanas 5–6 al implementar `load.py` y el DDL completo.*

**Decisión preliminar:** Particionamiento mensual por rango sobre `pickup_datetime` en `fact_viajes`.

**Justificación preliminar:** Con un promedio de 4,060,217 registros por mes y 12 meses en el dataset, la granularidad mensual produce 12 particiones de tamaño uniforme (~4M filas cada una). Las consultas del dashboard filtran frecuentemente por mes o trimestre, lo que permitirá demostrar partition pruning con `EXPLAIN ANALYZE` al escanear solo las particiones relevantes en lugar de los 48.7 millones de registros completos.

---

## 3. Índices

> *Esta sección se completará en las semanas 5–6 al documentar el impacto cuantitativo de cada índice con `EXPLAIN ANALYZE`.*

**Índices planificados:**

| Índice | Columnas | Consulta que lo motiva |
|---|---|---|
| `idx_fact_tiempo` | `tiempo_id` | Tendencia mensual de ingresos (pregunta de negocio 1) |
| `idx_fact_zona_pickup` | `zona_pickup_id` | Zonas con mayor volumen de viajes (pregunta de negocio 2) |
| `idx_fact_metodo_tiempo` | `id_metodo_pago, tiempo_id` | Distribución de pago por día de semana (pregunta de negocio 3) — índice compuesto |

---

## 4. Análisis OLTP vs. OLAP

> *Esta sección se completará en las semanas 7–8 al documentar el EXPLAIN ANALYZE completo.*

**Distinción preliminar:**

El **sistema fuente** (el sistema de taxis de NYC que genera los registros en tiempo real mediante los dispositivos TPEP instalados en cada taxi) opera bajo el paradigma **OLTP**: registra cada viaje de forma transaccional, con operaciones de escritura frecuentes y optimizado para insertar y consultar registros individuales.

El **Data Warehouse construido en este proyecto** es el componente **OLAP**: está optimizado para consultas analíticas agregadas sobre millones de registros, usando el esquema estrella con cinco dimensiones, particionamiento mensual por rango e índices estratégicos para acelerar los patrones de consulta del dashboard.
