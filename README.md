# Proyecto Final — Data Warehouse NYC Taxi Trip Records
**Base de Datos II — Universidad Mariano Gálvez de Guatemala**

---

## Descripción del Proyecto

Sistema completo de ingeniería de datos analíticos construido sobre los registros de viajes en taxi amarillo de Nueva York (NYC Yellow Taxi Trip Records — TLC). El proyecto implementa un pipeline ETL en Python, un Data Warehouse con esquema estrella en PostgreSQL 17, y un dashboard analítico conectado directamente a la base de datos.

**Dataset fuente:** [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)  
**Período cubierto:** Año 2025 completo (12 archivos Parquet mensuales)  
**Volumen estimado:** ~41 millones de registros en `fact_viajes` (superando el mínimo de 5M requerido)

---

## Equipo

| Integrante | Carné |
|---|---|
| Santiago Alexánder Pocón Buch | 7590-12-6162 |
| Valeria Melissa Guzmán Estrada | 7590-23-4125 |
| Luz Miriam Gil Aguilar | 7590-23-2193 |
| Cindy Beatriz Pú Getellá | 7590-17-14351 |

---

## Preguntas de Negocio del Dashboard

El dashboard responde las siguientes 4 preguntas analíticas, todas respondibles con el dataset elegido:

### 1. ¿Cuál es la tendencia mensual de ingresos totales generados por los viajes en taxi durante el año?
Permite identificar estacionalidad en los ingresos, picos por temporada (verano, fiestas) y meses con menor actividad. Usa `total_amount` agrupado por mes desde `dim_tiempo`.

### 2. ¿Cuáles son las zonas de recogida con mayor volumen de viajes y cuál es su tarifa promedio?
Identifica las zonas más demandadas de Nueva York (ej. aeropuertos, Midtown) y compara si las zonas con más viajes también generan las tarifas más altas. Combina `dim_zona` con `fact_viajes`.

### 3. ¿Cómo se distribuye el uso de medios de pago (tarjeta vs. efectivo) a lo largo de la semana?
Revela patrones de comportamiento del pasajero: si los fines de semana se paga más en efectivo, si los días laborales predomina la tarjeta, etc. Combina `dim_pago` con `dim_tiempo`.

### 4. ¿Qué proveedor de taxi (VendorID) genera mayor ingreso promedio por viaje y cuál tiene mayor proporción de viajes almacenados (store & forward)?
Compara el rendimiento operativo entre proveedores (Creative Mobile Technologies vs. Curb Mobility) e identifica zonas o rutas con problemas de conectividad. Usa `dim_taxi` y `fact_viajes`.

---

## Arquitectura del Sistema

```
Fuente (Parquet)
      │
      ▼
 etl/extract.py       ← Descarga automatizada desde nyc.gov
      │
      ▼
 etl/transform.py     ← Limpieza, construcción de dimensiones y hechos
      │
      ▼
  /staging/           ← Archivos Parquet/CSV transformados
      │
      ▼
  etl/load.py         ← Carga por lotes a PostgreSQL (COPY)
      │
      ▼
 PostgreSQL 17        ← Data Warehouse (esquema estrella + particiones + índices)
      │
      ▼
 Power BI / Tableau   ← Dashboard conectado directamente a PostgreSQL
```

---

## Estructura del Repositorio

```
proyecto-bdii/
├── etl/
│   ├── extract.py          # Descarga automatizada del dataset
│   ├── transform.py        # Limpieza y construcción de dimensiones/hechos
│   └── load.py             # Carga por lotes a PostgreSQL
├── staging/                # Archivos Parquet/CSV generados por transform.py
├── sql/
│   ├── ddl_schema.sql      # CREATE TABLE, particiones e índices
│   └── queries_analyze.sql # Consultas usadas en EXPLAIN ANALYZE
├── docs/
│   ├── dataset_profile.md  # Perfil del dataset: columnas, tipos, calidad
│   ├── model_draft.md      # Borrador del modelo dimensional
│   ├── model_diagram.png   # Diagrama dimensional (estrella)
│   ├── technical-decisions.md  # Decisiones técnicas justificadas
│   └── partition_notes.md  # Notas de particionamiento PostgreSQL 17
├── requirements.txt
└── README.md
```

---

## Modelo Dimensional

Esquema estrella con una tabla de hechos central y cuatro dimensiones:

| Tabla | Tipo | Descripción |
|---|---|---|
| `fact_viajes` | Hechos | Un registro por viaje (~41M filas) |
| `dim_tiempo` | Dimensión | Fecha, día, mes, trimestre, año, día de semana |
| `dim_zona` | Dimensión | Zonas TLC de NYC (role-playing: pickup y dropoff) |
| `dim_pago` | Dimensión | Tipo de pago y código de tarifa |
| `dim_taxi` | Dimensión | Proveedor del servicio y tipo de almacenamiento |

Ver detalles completos en [`docs/model_draft.md`](docs/model_draft.md) y diagrama en [`docs/model_diagram.png`](docs/model_diagram.png).

---

## Cómo Levantar el Entorno

### Requisitos previos
- Docker Desktop instalado y corriendo
- Python 3.9 o superior
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/<tu-usuario>/proyecto-bdii.git
cd proyecto-bdii
```

### 2. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 3. Levantar PostgreSQL 17 con Docker

```bash
docker compose up -d
```

Verificar que el contenedor está corriendo:

```bash
docker ps
```

Verificar conexión a PostgreSQL:

```bash
docker exec -it postgres_bdii psql -U bdii_user -d nyc_taxi_dw
```

**Credenciales por defecto (solo desarrollo local):**

| Parámetro | Valor |
|---|---|
| Host | `localhost` |
| Puerto | `5432` |
| Base de datos | `nyc_taxi_dw` |
| Usuario | `bdii_user` |
| Contraseña | `bdii_pass` |

### 4. Ejecutar el pipeline ETL completo

```bash
python etl/extract.py
python etl/transform.py
python etl/load.py
```

> **Tiempo estimado de carga:** 25–40 minutos para 1 año completo (~41M registros) en una máquina local estándar usando `COPY` de PostgreSQL.

---

## Dependencias

Ver [`requirements.txt`](requirements.txt) para la lista completa. Principales:

- `pandas` — manipulación de datos
- `pyarrow` — lectura de archivos Parquet
- `psycopg2-binary` — conexión a PostgreSQL desde Python
- `python-dotenv` — manejo de variables de entorno

---

## Decisiones Técnicas

Ver [`docs/technical-decisions.md`](docs/technical-decisions.md) para la justificación completa de:
- Elección de esquema estrella sobre snowflake
- Estrategia de particionamiento mensual de `fact_viajes`
- Justificación y comparación de rendimiento de índices
- Diferencia entre el sistema OLTP fuente (sistema de taxis de NYC) y el DW OLAP construido

---

## Dataset

- **Fuente principal:** [NYC TLC Yellow Taxi Trip Records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- **Fuente secundaria:** [NYC Taxi Zones](https://source.coop/cholmes/nyc-taxi-zones)
- **Formato:** Parquet
- **Volumen:** ~3.47M registros/mes → ~41M registros/año

Ver perfil detallado en [`docs/dataset_profile.md`](docs/dataset_profile.md).

## Preguntas para el Catedrático

Durante el desarrollo de las semanas 1 y 2 surgieron las siguientes dudas técnicas que el equipo quiere clarificar antes de avanzar a la implementación del ETL:

### Sobre el Modelo Dimensional

1. **¿Se acepta separar `dim_pago` en dos dimensiones independientes (`dim_metodo_pago` y `dim_tarifa_pago`)?**  
   El modelo actual separa el método de pago (tarjeta, efectivo, etc.) de la tarifa aplicada (estándar, JFK, Newark, etc.) porque son conceptos independientes — un viaje puede tener cualquier combinación de ambos. ¿Este diseño sigue siendo esquema estrella o se considera snowflake?

2. **Para la dimensión de tiempo, ¿`dia_semana` debe almacenarse como texto (`Wednesday`) o como número (1–7)?**  
   El modelo actual usa `VARCHAR(10)` con el nombre del día. Si el dashboard necesita ordenar por día de semana, un número puede ser más eficiente para el ORDER BY.

3. **¿El campo `geometry` del dataset secundario de zonas debe incluirse en alguna tabla del Data Warehouse o se descarta completamente?**  
   Actualmente el diseño lo excluye del modelo relacional. ¿Podría ser relevante para alguna visualización en el dashboard?

### Sobre el ETL

4. **Para la carga por lotes con `COPY` de PostgreSQL, ¿cuál es el tamaño de lote recomendado para un dataset de ~48.7M registros?**  
   El equipo planea procesar en lotes mensuales (un archivo Parquet por mes), pero no está seguro si conviene subdividir más dentro de cada mes.
