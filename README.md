# Proyecto Final — Data Warehouse NYC Taxi Trip Records
**Base de Datos II — Universidad Mariano Gálvez de Guatemala**

---

## Descripción del Proyecto

Sistema completo de ingeniería de datos analíticos construido sobre los registros de viajes en taxi amarillo de Nueva York (NYC Yellow Taxi Trip Records — TLC). El proyecto implementa un pipeline ETL en Python, un Data Warehouse con esquema estrella en PostgreSQL 17, y un dashboard analítico conectado directamente a la base de datos.

**Dataset fuente:** [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)  
**Período cubierto:** Año 2025 completo (12 archivos Parquet mensuales)  
**Volumen:** 35,721,060 registros en `fact_viajes`

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

El dashboard responde las siguientes 4 preguntas analíticas:

### 1. ¿Cuál es la tendencia mensual de ingresos totales generados por los viajes en taxi durante el año?
Permite identificar estacionalidad en los ingresos, picos por temporada (verano, fiestas) y meses con menor actividad. Usa `total_amount` agrupado por mes desde `dim_tiempo`.

### 2. ¿Cuáles son las zonas de recogida con mayor volumen de viajes y cuál es su tarifa promedio?
Identifica las zonas más demandadas de Nueva York (ej. aeropuertos, Midtown) y compara si las zonas con más viajes también generan las tarifas más altas. Combina `dim_zona` con `fact_viajes`.

### 3. ¿Cómo se distribuye el uso de medios de pago (tarjeta vs. efectivo) a lo largo de la semana?
Revela patrones de comportamiento del pasajero. Combina `dim_metodo_pago` con `dim_tiempo`.

### 4. ¿Qué proveedor de taxi genera mayor ingreso promedio por viaje y cuál tiene mayor proporción de viajes almacenados?
Compara el rendimiento operativo entre proveedores. Usa `dim_proveedor` y `fact_viajes`.

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
  /staging/           ← Archivos Parquet generados por transform.py
      │
      ▼
  etl/load.py         ← Ejecuta el DDL, limpia tablas y carga datos a PostgreSQL via Docker (COPY)
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
│   └── load.py             # Ejecuta DDL y carga por lotes a PostgreSQL
├── staging/                # Archivos Parquet generados por transform.py
├── sql/
│   ├── ddl_schema.sql      # CREATE TABLE, particiones e índices
│   └── queries_analyze.sql # Consultas usadas en EXPLAIN ANALYZE
├── docs/
│   ├── dataset_profile.md  # Perfil del dataset: columnas, tipos, calidad
│   ├── model_draft.md      # Borrador del modelo dimensional
│   ├── model_diagram.png   # Diagrama dimensional (estrella)
│   └── technical-decisions.md  # Decisiones técnicas justificadas
├── requirements.txt
└── README.md
```

---

## Modelo Dimensional

Esquema estrella con una tabla de hechos central y cinco dimensiones:

| Tabla | Tipo | Descripción |
|---|---|---|
| `fact_viajes` | Hechos | Un registro por viaje (35.7M filas) |
| `dim_tiempo` | Dimensión | Fecha, día, mes, trimestre, año, día de semana |
| `dim_zona` | Dimensión | Zonas TLC de NYC (role-playing: pickup y dropoff) |
| `dim_metodo_pago` | Dimensión | Tipo de pago (tarjeta, efectivo, etc.) |
| `dim_tarifa_pago` | Dimensión | Código de tarifa (estándar, JFK, Newark, etc.) |
| `dim_proveedor` | Dimensión | Proveedor del servicio y tipo de almacenamiento |

---

## Cómo Levantar el Entorno

### Requisitos previos
- Docker Desktop instalado y corriendo
- Python 3.9 o superior
- Git

---

### 1. Clonar el repositorio

Crear una carpeta donde se quiera descargar el proyecto, por ejemplo `C:\Proyectos`. Abrir PowerShell dentro de esa carpeta y ejecutar:

```powershell
git clone https://github.com/BeaGetella7/proyecto-BDII.git
```

Esto crea una carpeta llamada `proyecto-BDII`. Entrar a ella:

```powershell
cd proyecto-BDII
```

> Todos los comandos siguientes deben ejecutarse desde dentro de la carpeta `proyecto-BDII`. Verificar que la terminal muestre la ruta correcta antes de continuar.

---

### 2. Instalar dependencias de Python

Desde dentro de la carpeta `proyecto-BDII` ejecutar:

**Windows:** Si `pip` no se reconoce como comando, usar:
```bash
py -m pip
```

```powershell
pip install -r requirements.txt --only-binary=:all:
```

Verificar que las dependencias quedaron instaladas correctamente:

```powershell
pip show pandas pyarrow psycopg
```

Deben aparecer las tres librerías con sus versiones. Si alguna no aparece, el comando anterior no se ejecutó correctamente.

---

### 3. Levantar PostgreSQL con Docker

Abrir Docker Desktop y esperar a que cargue completamente. Luego, desde dentro de la carpeta `proyecto-BDII`, ejecutar:

```powershell
docker compose up -d
```

Verificar que el contenedor está corriendo:

```powershell
docker ps
```

Debe aparecer una línea con `bdii_postgres` y estado `Up`. Si no aparece, verificar que Docker Desktop esté abierto y volver a ejecutar `docker compose up -d`.

**Credenciales de la base de datos:**

| Parámetro | Valor |
|---|---|
| Host | `localhost` |
| Puerto | `5432` |
| Base de datos | `datawarehouse` |
| Usuario | `bdii_user` |
| Contraseña | `bdii_password123` |

---

### 4. Ejecutar el pipeline ETL

Ejecutar los tres scripts en orden desde dentro de la carpeta `proyecto-BDII`:

**Windows:** Si aparece _"Python was not found"_, usar `py` en lugar de `python`:
```bash
py
```

```powershell
python etl/extract.py
```

```powershell
python etl/transform.py
```

```powershell
python etl/load.py
```

> No ejecutar el siguiente script hasta que el anterior haya terminado completamente.

> `load.py` se encarga de crear automáticamente todas las tablas, particiones e índices en PostgreSQL antes de cargar los datos. No es necesario ejecutar el DDL manualmente.

| Script | Descripción | Tiempo estimado |
|---|---|---|
| `extract.py` | Descarga los 12 archivos Parquet de NYC TLC + tabla de zonas | 15–30 min |
| `transform.py` | Limpia los datos y construye dimensiones y tabla de hechos | 10–20 min |
| `load.py` | Ejecuta el DDL, limpia tablas y carga los datos a PostgreSQL via Docker usando COPY | 30–40 min |

> **Tiempo total estimado:** entre 55 y 90 minutos para el año completo en una máquina local estándar. El tiempo real medido fue de 34.4 minutos solo en la carga.

---

### 5. Verificar la carga

Al finalizar `load.py` se imprime el conteo de cada tabla automáticamente. También se puede verificar manualmente entrando a la base de datos:

```powershell
docker exec -it bdii_postgres psql -U bdii_user -d datawarehouse
```

Dentro de psql ejecutar:

```sql
SELECT COUNT(*) FROM fact_viajes;
SELECT COUNT(*) FROM dim_tiempo;
SELECT COUNT(*) FROM dim_zona;
\q
```

`fact_viajes` debe tener aproximadamente 35,721,060 filas. El `\q` cierra la conexión.

---

## Si algo falla — limpiar y empezar de nuevo

Si se necesita limpiar todo y empezar desde cero, ejecutar estos comandos en orden desde dentro de la carpeta `proyecto-BDII`:

```powershell
docker compose down -v
```

```powershell
docker compose up -d
```

Luego volver al paso 4 y ejecutar el pipeline de nuevo. `load.py` se encarga de recrear el esquema automáticamente.

Si ya se descargaron los archivos del extract y solo se necesita volver a transformar y cargar:

```powershell
del staging\dim_*.parquet
del staging\fact_viajes_*.parquet
python etl/transform.py
python etl/load.py
```

---

## Dependencias

Ver [`requirements.txt`](requirements.txt) para la lista completa. Principales:

- `pandas` — manipulación de datos
- `pyarrow` — lectura de archivos Parquet
- `psycopg` — conexión a PostgreSQL desde Python (compatible con Python 3.13+)
- `requests` — descarga automatizada de archivos
- `tqdm` — barra de progreso durante la descarga

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
- **Volumen:** ~3.47M registros/mes → 35.7M registros/año (después de limpieza)