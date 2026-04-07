# Documento de Decisiones Técnicas
**Proyecto:** NYC Taxi Trip Records — Data Warehouse  
**Curso:** Base de Datos II — Universidad Mariano Gálvez de Guatemala  
**Última actualización:** Abril 2025

---

## 1. Elección del Modelo Dimensional: Esquema Estrella

### Decisión

Se eligió el **esquema estrella** compuesto por una tabla de hechos central (`fact_viajes`) y cuatro tablas de dimensiones desnormalizadas: `dim_tiempo`, `dim_zona`, `dim_pago` y `dim_taxi`.

Se descartó el **esquema snowflake** como alternativa.

---

### ¿Por qué estrella y no snowflake?

#### Argumento 1 — Las dimensiones del dataset no tienen jerarquías complejas que justifiquen normalización adicional

En el esquema snowflake, las dimensiones se normalizan dividiéndolas en subtablas para eliminar redundancia. Esto tiene sentido cuando una dimensión tiene jerarquías profundas con muchos valores distintos en cada nivel.

En nuestro caso, las dimensiones son intrínsecamente planas:

- `dim_pago` tiene solo 7 valores posibles en `payment_type` y 7 en `RatecodeID`. Crear una tabla separada `dim_tipo_pago` y otra `dim_tarifa` para normalizar estos catálogos no elimina redundancia significativa: cada tabla tendría menos de 10 filas. El costo de un JOIN adicional en cada consulta supera ampliamente el beneficio de almacenamiento.

- `dim_taxi` tiene 4 proveedores distintos (`VendorID`: 1, 2, 6, 7) y 2 valores en `store_and_fwd_flag`. Normalizar estos campos en subtablas separadas añadiría JOINs sin reducir el volumen de datos de forma apreciable.

- `dim_zona` tiene 263 zonas únicas (`LocationID`) con sus atributos `zone`, `borough`, `shape_area` y `shape_leng`. No existe una jerarquía natural que requiera descomposición: el `borough` es un atributo de la zona, no una entidad independiente con sus propios atributos relacionados.

**Conclusión:** La normalización adicional del snowflake no elimina redundancia real en nuestro dataset; solo agrega complejidad de consulta sin beneficio proporcional.

---

#### Argumento 2 — El volumen de `fact_viajes` (~41M filas) hace que el costo de JOINs adicionales sea relevante

El esquema snowflake requiere más JOINs por consulta porque las dimensiones están fragmentadas en subtablas. Con una tabla de hechos de ~41 millones de registros, cada JOIN adicional tiene un costo de ejecución medible.

El optimizador de PostgreSQL debe resolver más relaciones por consulta en un esquema snowflake. En consultas analíticas típicas del dashboard (ej. ingresos por mes y zona, distribución de pago por día de semana), el esquema estrella permite al planificador acceder a todas las columnas de una dimensión en una sola lectura de tabla, sin encadenar múltiples JOINs.

Ejemplo concreto: la consulta que responde la pregunta de negocio 3 (distribución de medios de pago por día de semana) necesita unir `fact_viajes` con `dim_pago` y `dim_tiempo`. En un esquema snowflake normalizado, `dim_pago` podría dividirse en `dim_pago → dim_tipo_pago → dim_tarifa`, convirtiendo un JOIN en tres. Con 41M de filas en la tabla de hechos, esto incrementa el costo del plan de ejecución de forma innecesaria.

**Conclusión:** El esquema estrella minimiza el número de JOINs por consulta, lo que es directamente relevante para el rendimiento cuando la tabla de hechos supera los 40 millones de registros.

---

#### Argumento 3 — `dim_zona` actúa como dimensión de rol: el esquema estrella soporta este patrón de forma nativa y eficiente

Una de las características más importantes de nuestro modelo es que `dim_zona` se usa dos veces en `fact_viajes`: una para la zona de recogida (`zona_pickup_id`) y otra para la zona de entrega (`zona_dropoff_id`). Este patrón se llama **dimensión de rol** (*role-playing dimension*).

En el esquema estrella, este patrón se implementa directamente: la misma tabla `dim_zona` se une a `fact_viajes` con dos alias distintos (`zona_pickup` y `zona_dropoff`). La consulta es legible y el planificador puede usar el mismo índice sobre `zona_id` para ambas uniones.

En un esquema snowflake, si `dim_zona` estuviera normalizada (ej. separando `dim_borough` como subtabla), cada unión de rol requeriría seguir la cadena de subtablas, duplicando la complejidad de la consulta para cada uno de los dos roles.

**Conclusión:** El patrón de dimensión de rol de `dim_zona` se expresa de forma más simple y eficiente en el esquema estrella. El snowflake añadiría complejidad de consulta sin beneficio analítico.

---

### Tabla resumen de la decisión

| Criterio | Estrella | Snowflake |
|---|---|---|
| Número de JOINs por consulta | Mínimo (1 por dimensión) | Mayor (puede ser 2–3 por dimensión) |
| Complejidad para el analista | Baja — todas las columnas en una tabla | Mayor — requiere conocer la jerarquía de subtablas |
| Redundancia de datos en dimensiones | Baja (dimensiones pequeñas <263 filas) | Marginal — no hay jerarquías profundas que normalizar |
| Soporte para dimensión de rol (`dim_zona`) | Nativo y simple | Más complejo con subtablas encadenadas |
| Rendimiento con 41M filas en `fact_viajes` | Mejor — menos operaciones por consulta | Menor — JOINs adicionales a escala |

---

## 2. Estrategia de Particionamiento

> *Esta sección se completará en las semanas 5–6 al implementar `load.py` y el DDL completo.*

**Decisión preliminar:** Particionamiento mensual por rango sobre `pickup_datetime` en `fact_viajes`.

**Justificación preliminar:** Con ~3.47M registros por mes y 12 meses en el dataset, la granularidad mensual produce 12 particiones de tamaño uniforme. Las consultas del dashboard filtran frecuentemente por mes o trimestre, lo que permitirá demostrar partition pruning con `EXPLAIN ANALYZE` al escanear solo las particiones relevantes.

---

## 3. Índices

> *Esta sección se completará en las semanas 5–6 al documentar el impacto cuantitativo de cada índice con `EXPLAIN ANALYZE`.*

**Índices planificados:**

| Índice | Columnas | Consulta que lo motiva |
|---|---|---|
| `idx_fact_tiempo` | `tiempo_id` | Tendencia mensual de ingresos (pregunta 1) |
| `idx_fact_zona_pickup` | `zona_pickup_id` | Zonas con mayor volumen de viajes (pregunta 2) |
| `idx_fact_pago_tiempo` | `pago_id, tiempo_id` | Distribución de pago por día de semana (pregunta 3) — índice compuesto |

---

## 4. Análisis OLTP vs. OLAP

> *Esta sección se completará en las semanas 7–8 al documentar el EXPLAIN ANALYZE completo.*

**Distinción preliminar:**

El **sistema fuente** (el sistema de taxis de NYC que genera los registros en tiempo real mediante los dispositivos TPEP instalados en cada taxi) opera bajo el paradigma **OLTP**: registra cada viaje de forma transaccional, con operaciones de escritura frecuentes, alta concurrencia y optimizado para insertar y consultar registros individuales.

El **Data Warehouse construido en este proyecto** es el componente **OLAP**: está optimizado para consultas analíticas agregadas sobre millones de registros, usando el esquema estrella, particionamiento por rango e índices estratégicos para acelerar los patrones de consulta del dashboard.
