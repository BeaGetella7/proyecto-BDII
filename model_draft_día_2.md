# Borrador del Modelo Dimensional — Esquema Estrella
**Proyecto:** NYC Taxi Trip Records — Data Warehouse  
**Responsable:** Valeria Melissa Guzman Estrada  
**Basado en:** `docs/dataset_profile.md` (Santiago)  
**Fecha:** Abril 2025

---

## Descripción General

Se propone un **esquema estrella** compuesto por una tabla central de hechos (`fact_viajes`) y cinco tablas de dimensiones (`dim_tiempo`, `dim_zona`, `dim_proveedor`, `dim_metodo_pago`, `dim_tarifa_pago`).

Este modelo permite responder preguntas de negocio sobre los viajes en taxi de Nueva York de forma eficiente, minimizando la cantidad de JOINs necesarios en cada consulta analítica.

---

## Tablas del Modelo

### 1. `dim_tiempo`
Contiene la información temporal derivada de las fechas de los viajes. Se construye a partir de `tpep_pickup_datetime`.

| Columna            | Tipo        | Descripción                                      | Ejemplo     |
|--------------------|-------------|--------------------------------------------------|-------------|
| `tiempo_id`        | INT (PK)    | GENERATED ALWAYS AS IDENTITY                     | 1, 2, 3     |
| `fecha`            | DATE        | Fecha completa del viaje                         | 2025-01-15  |
| `dia`              | SMALLINT    | Día del mes                                      | 15          |
| `mes`              | SMALLINT    | Número del mes                                   | 1           |
| `trimestre`        | SMALLINT    | Trimestre del año (1–4)                          | 1           |
| `anio`             | SMALLINT    | Año                                              | 2025        |
| `dia_semana`       | VARCHAR(10) | Nombre del día (Monday, Tuesday…)                | Wednesday   |
| `es_fin_de_semana` | BOOLEAN     | TRUE si es sábado o domingo                      | FALSE       |

**Fuente:** Columna `tpep_pickup_datetime` del dataset principal.  
**Nota de calidad:** El rango válido de fechas es enero 2025. El ETL debe excluir registros con `tpep_pickup_datetime` fuera de este rango, ya que el dataset contiene fechas desde 2024-12-18 hasta 2025-02-01.

---

### 2. `dim_zona`
Contiene la información geográfica de las zonas de taxi de Nueva York. Se construye a partir del dataset secundario (tabla de zonas).

| Columna       | Tipo        | Descripción                                                    | Ejemplo         |
|---------------|-------------|----------------------------------------------------------------|-----------------|
| `zona_id`     | INT (PK)    | GENERATED ALWAYS AS IDENTITY                                   | 1, 2, 3         |
| `location_id` | INT         | ID original de la zona (vincula con PULocationID/DOLocationID) | 79, 161         |
| `zone`        | VARCHAR(60) | Nombre del barrio o área de la zona                            | Midtown Center  |
| `borough`     | VARCHAR(30) | Distrito de Nueva York donde se ubica la zona                  | Manhattan       |
| `shape_area`  | FLOAT       | Área del polígono de la zona                                   | 0.00078230679   |
| `shape_leng`  | FLOAT       | Longitud del perímetro del polígono de la zona                 | 0.11635745319   |

**Fuente:** Dataset secundario (tabla de zonas TLC).  
**Nota:** Esta dimensión se usa dos veces en `fact_viajes`: una para la zona de recogida (`zona_pickup_id`) y otra para la zona de entrega (`zona_dropoff_id`). Es una **dimensión de rol** (role-playing dimension). Es la misma tabla usada dos veces con distinto propósito.

---

### 3. `dim_proveedor`
Contiene información sobre el proveedor del servicio de taxi y el tipo de registro del viaje.

| Columna               | Tipo        | Descripción                                              | Ejemplo                      |
|-----------------------|-------------|----------------------------------------------------------|------------------------------|
| `proveedor_id`        | INT (PK)    | GENERATED ALWAYS AS IDENTITY                             | 1, 2, 3                      |
| `vendor_id`           | SMALLINT    | Código del proveedor TPEP original                       | 1, 2, 6, 7                   |
| `vendor_nombre`       | VARCHAR(50) | Nombre del proveedor                                     | Creative Mobile Technologies |
| `store_and_fwd_flag`  | CHAR(1)     | Indica si el viaje se almacenó antes de enviarse         | Y, N                         |
| `tipo_almacenamiento` | VARCHAR(35) | Descripción del flag de almacenamiento                   | Viaje de almacenamiento       |

**Fuente:** Columnas `VendorID` y `store_and_fwd_flag` del dataset principal.  
**Referencia de códigos:**
- `VendorID`: 1=Creative Mobile Technologies LLC, 2=Curb Mobility LLC, 6=Myle Technologies Inc, 7=Helix
- `store_and_fwd_flag`: Y=Viaje almacenado y reenviado por falta de señal, N=Envío directo en tiempo real

**Nota:** TPEP (Taxicab Passenger Enhancement Program) es el sistema instalado dentro del taxi que registra automáticamente cuándo arrancó el viaje, cuándo terminó, cuánto marcó el taxímetro y cómo pagó el pasajero.

---

### 4. `dim_metodo_pago`
Contiene los tipos de pago disponibles para los viajes.

| Columna               | Tipo        | Descripción                               | Ejemplo            |
|-----------------------|-------------|-------------------------------------------|--------------------|
| `id_metodo_pago`      | INT (PK)    | GENERATED ALWAYS AS IDENTITY              | 1, 2, 3            |
| `payment_type`        | VARCHAR(10) | Código numérico original del tipo de pago | 1, 2, 3            |
| `payment_descripcion` | VARCHAR(30) | Descripción del tipo de pago              | Tarjeta de crédito |

**Fuente:** Columna `payment_type` del dataset principal.  
**Referencia de códigos:**

| Código | Descripción |
|--------|-------------|
| 0 | Tarifa flexible |
| 1 | Tarjeta de crédito |
| 2 | Efectivo |
| 3 | Sin cargo |
| 4 | Disputa: el pasajero impugnó el cobro ante su banco |
| 5 | Desconocido |
| 6 | Viaje anulado |

---

### 5. `dim_tarifa_pago`
Contiene los tipos de tarifa aplicables a los viajes.

| Columna                | Tipo        | Descripción                               | Ejemplo         |
|------------------------|-------------|-------------------------------------------|-----------------|
| `ratecode_id`          | INT (PK)    | GENERATED ALWAYS AS IDENTITY              | 1, 2, 3         |
| `ratecode_descripcion` | VARCHAR(40) | Descripción de la tarifa                  | Tarifa estándar |

**Fuente:** Columna `RatecodeID` del dataset principal.  
**Referencia de códigos:**

| Código | Situación real |
|--------|----------------|
| 1 | Tarifa estándar: el taxímetro cobra por tiempo y distancia |
| 2 | JFK: tarifa fija entre Manhattan y el aeropuerto JFK |
| 3 | Newark: tarifa especial hacia New Jersey (cruza estado) |
| 4 | Nassau/Westchester: viajes a suburbios fuera de NYC |
| 5 | Negociada: pasajero y taxista acordaron precio antes de salir |
| 6 | Grupo: viaje compartido, varios pasajeros dividen el costo |
| 99 | Desconocido: dato no registrado o error del sistema |

---

### 6. `fact_viajes`
Tabla central del esquema. Cada fila representa un viaje individual en taxi. Contiene las métricas numéricas y las claves foráneas hacia las dimensiones.

| Columna                 | Tipo        | Descripción                                                         | Ejemplo             |
|-------------------------|-------------|---------------------------------------------------------------------|---------------------|
| `viaje_id`              | BIGINT (PK) | GENERATED ALWAYS AS IDENTITY                                        | 1, 2, 3             |
| `tiempo_id`             | INT (FK)    | Referencia a `dim_tiempo`                                           | 42                  |
| `zona_pickup_id`        | INT (FK)    | Referencia a `dim_zona` (zona de recogida)                          | 15                  |
| `zona_dropoff_id`       | INT (FK)    | Referencia a `dim_zona` (zona de entrega)                           | 87                  |
| `id_metodo_pago`        | INT (FK)    | Referencia a `dim_metodo_pago`                                      | 1                   |
| `proveedor_id`          | INT (FK)    | Referencia a `dim_proveedor`                                        | 2                   |
| `ratecode_id`           | INT (FK)    | Referencia a `dim_tarifa_pago`                                      | 1                   |
| `pickup_datetime`       | TIMESTAMP   | Fecha y hora exacta de inicio del viaje                             | 2025-01-15 08:32:10 |
| `dropoff_datetime`      | TIMESTAMP   | Fecha y hora exacta de fin del viaje                                | 2025-01-15 08:51:44 |
| `passenger_count`       | INTEGER     | Número de pasajeros en el viaje                                     | 1, 3                |
| `trip_distance`         | FLOAT       | Distancia del viaje en millas                                       | 3.35                |
| `fare_amount`           | FLOAT       | Tarifa base calculada por el medidor                                | 15.85               |
| `extra`                 | FLOAT       | Extras y recargos varios                                            | 0.50                |
| `mta_tax`               | FLOAT       | Impuesto MTA de $0.50 fijos por viaje para financiar transporte público | 0.50            |
| `tip_amount`            | FLOAT       | Propina (solo tarjeta de crédito, propinas en efectivo no incluidas)| 2.00                |
| `tolls_amount`          | FLOAT       | Total de peajes pagados                                             | 0.00                |
| `improvement_surcharge` | FLOAT       | Recargo por mejoras (desde 2015)                                    | 1.00                |
| `congestion_surcharge`  | FLOAT       | Recargo de congestión del estado de Nueva York                      | 2.50                |
| `airport_fee`           | FLOAT       | Cargo por recogida en LaGuardia o JFK                               | 1.75                |
| `cbd_congestion_fee`    | FLOAT       | Cargo de congestión MTA (desde el 5 enero 2025)                     | 0.75                |
| `total_amount`          | FLOAT       | Monto total cobrado al pasajero (sin propinas en efectivo)          | 20.60               |

**Fuente:** Dataset principal `yellow_tripdata_2025-01.parquet`.  
**Volumen estimado:** ~3.47M filas por mes → aprox. **48.7M filas** para un año completo, superando el mínimo de 5M requerido.

---

## Relaciones del Modelo

```
dim_tiempo        ──< fact_viajes >── dim_zona        (pickup)
                                  └─ dim_zona        (dropoff)
dim_proveedor     ──< fact_viajes
dim_metodo_pago   ──< fact_viajes
dim_tarifa_pago   ──< fact_viajes
```

Cada viaje en `fact_viajes` se conecta con:
- **1 registro** en `dim_tiempo` (cuándo salió el taxi)
- **2 registros** en `dim_zona` (de dónde salió y a dónde llegó)
- **1 registro** en `dim_proveedor` (qué proveedor operó el taxi)
- **1 registro** en `dim_metodo_pago` (cómo pagó el pasajero)
- **1 registro** en `dim_tarifa_pago` (qué tarifa aplicó al viaje)

Todas las relaciones son **uno a muchos**: una dimensión puede estar en muchos viajes, pero cada viaje pertenece a exactamente una dimensión de cada tipo.

---

## Problemas de Calidad Incorporados

Reportados por Santiago en `dataset_profile.md`. El ETL debe manejar los siguientes casos antes de cargar los datos:

| Problema | Columnas afectadas | Acción en ETL |
|---|---|---|
| Fechas fuera de rango | `tpep_pickup_datetime`, `tpep_dropoff_datetime` | Excluir registros fuera de enero 2025 |
| Valores NaN y None | Múltiples columnas (~3.89%) | Aplicar valor por defecto o excluir según regla de negocio |
| Valores negativos en campos numéricos | `fare_amount`, `tip_amount`, `total_amount` y otros montos | Excluir o corregir registros con valores negativos |
| `passenger_count` debe ser entero | `passenger_count` | Convertir a INTEGER, excluir valores 0 o negativos |
| Registros duplicados | Dataset completo | Deduplicar antes de cargar |
| Carga por lotes | Dataset completo | Procesar en lotes para manejar el volumen de ~48.7M registros anuales |

---

## Notas de Diseño

- Todas las dimensiones y `fact_viajes` usan **surrogate keys** (`GENERATED ALWAYS AS IDENTITY`) para desacoplar el modelo del sistema fuente. Esto significa que PostgreSQL genera el ID automáticamente y no se puede insertar un valor manual, garantizando integridad.
- `dim_zona` actúa como **dimensión de rol**: la misma tabla se une dos veces a `fact_viajes` con alias distintos (`zona_pickup` y `zona_dropoff`).
- `dim_metodo_pago` y `dim_tarifa_pago` se mantienen como dimensiones independientes porque el método de pago y la tarifa son conceptos separados — un viaje puede tener tarifa JFK y pagarse en efectivo, o tarifa estándar y pagarse con tarjeta.
- Los timestamps `pickup_datetime` y `dropoff_datetime` se conservan en `fact_viajes` para calcular duración del viaje (`dropoff_datetime - pickup_datetime`).
- El campo `geometry` del dataset secundario no se incluye en el modelo relacional; se puede usar en análisis geoespaciales separados.

---

## Regla para distinguir Hechos de Dimensiones

- **¿Este dato se suma o se promedia para sacar conclusiones?** → Va en `fact_viajes`. Ejemplo: ¿cuánto se ganó esta semana? Se suma `total_amount`. ¿Cuál es la propina promedio? Se promedia `tip_amount`.
- **¿Este dato describe el contexto del viaje?** → Va en una dimensión. Ejemplo: ¿fue de miércoles? → `dim_tiempo`. ¿Salió de Manhattan? → `dim_zona`.

---