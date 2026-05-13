import io
import time
import subprocess
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────
CONTAINER    = "bdii_postgres"
DB_NAME      = "datawarehouse"
DB_USER      = "bdii_user"
STAGING      = Path("staging")
TAMANIO_LOTE = 100_000

# ─────────────────────────────────────────────────────────────────────────────
# EJECUTAR SQL VIA DOCKER
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_sql(sql):
    """Ejecuta un comando SQL directo en PostgreSQL via Docker."""
    resultado = subprocess.run(
        ["docker", "exec", "-i", CONTAINER,
         "psql", "-U", DB_USER, "-d", DB_NAME, "-c", sql],
        capture_output=True, text=True
    )
    if resultado.returncode != 0:
        raise Exception(f"Error SQL: {resultado.stderr}")
    return resultado.stdout

def verificar_conexion():
    """Verifica que Docker y PostgreSQL estén corriendo."""
    try:
        ejecutar_sql("SELECT 1;")
        print("[OK] Conexión a PostgreSQL establecida via Docker.")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar: {e}")
        print("  Verifica que Docker esté corriendo: docker compose up -d")
        raise

def limpiar_tablas():
    """Limpia todas las tablas antes de cargar."""
    print("\n[INFO] Limpiando tablas...")
    ejecutar_sql("TRUNCATE TABLE fact_viajes CASCADE;")
    ejecutar_sql("TRUNCATE TABLE dim_tiempo, dim_zona, dim_proveedor, dim_metodo_pago, dim_tarifa_pago CASCADE;")
    print("[OK] Tablas limpias.")

# ─────────────────────────────────────────────────────────────────────────────
# CARGA CON COPY VIA DOCKER
# ─────────────────────────────────────────────────────────────────────────────

def cargar_con_copy(df, tabla):
    """
    Carga un DataFrame a PostgreSQL usando COPY FROM STDIN via Docker.
    Es el método más rápido — nunca INSERT por fila.
    """
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="\\N")
    csv_data = buffer.getvalue().encode("utf-8")

    columnas = ", ".join(df.columns)
    comando = f"COPY {tabla} ({columnas}) FROM STDIN WITH CSV NULL '\\N'"

    resultado = subprocess.run(
        ["docker", "exec", "-i", CONTAINER,
         "psql", "-U", DB_USER, "-d", DB_NAME, "-c", comando],
        input=csv_data,
        capture_output=True
    )

    if resultado.returncode != 0:
        raise Exception(f"Error COPY: {resultado.stderr.decode()}")

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE DIMENSIONES
# ─────────────────────────────────────────────────────────────────────────────

def cargar_dimension(nombre_archivo, tabla, columnas):
    """Carga una dimensión completa de una vez."""
    ruta = STAGING / f"{nombre_archivo}.parquet"

    if not ruta.exists():
        print(f"[SKIP] {ruta.name} no encontrado en staging/.")
        return

    df = pd.read_parquet(ruta, columns=columnas)
    print(f"[INFO] Cargando {tabla} ({len(df):,} filas)...")

    t0 = time.time()
    cargar_con_copy(df, tabla)
    elapsed = time.time() - t0

    print(f"[OK] {tabla} cargada en {elapsed:.1f}s")

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE FACT_VIAJES
# ─────────────────────────────────────────────────────────────────────────────

def cargar_fact_viajes():
    """Carga fact_viajes leyendo un archivo por mes en lotes."""
    archivos = sorted(STAGING.glob("fact_viajes_2025-*.parquet"))

    if not archivos:
        print("[ERROR] No se encontraron archivos fact_viajes_2025-*.parquet en staging/.")
        print("  Ejecuta primero: python etl/transform.py")
        return

    columnas = [
        "tiempo_id", "zona_pickup_id", "zona_dropoff_id",
        "id_metodo_pago", "proveedor_id", "ratecode_id",
        "pickup_datetime", "dropoff_datetime",
        "passenger_count", "trip_distance",
        "fare_amount", "extra", "mta_tax", "tip_amount",
        "tolls_amount", "improvement_surcharge",
        "congestion_surcharge", "airport_fee",
        "cbd_congestion_fee", "total_amount"
    ]

    total_filas_cargadas = 0
    t0_total = time.time()

    for archivo in archivos:
        print(f"\n[INFO] Cargando {archivo.name}...")
        df = pd.read_parquet(archivo, columns=columnas)

        # Renombrar ratecode_id a id_tarifa para que coincida con el DDL
        df = df.rename(columns={"ratecode_id": "id_tarifa"})

        # Convertir FK a entero
        cols_entero = [
            "tiempo_id", "zona_pickup_id", "zona_dropoff_id",
            "id_metodo_pago", "proveedor_id", "id_tarifa",
            "passenger_count"
        ]
        for col in cols_entero:
            if col in df.columns:
                df[col] = df[col].fillna(0).astype(int)

        total_filas = len(df)
        total_lotes = (total_filas // TAMANIO_LOTE) + 1

        t0 = time.time()

        for i in range(0, total_filas, TAMANIO_LOTE):
            lote = df.iloc[i : i + TAMANIO_LOTE]
            cargar_con_copy(lote, "fact_viajes")

            lote_num = (i // TAMANIO_LOTE) + 1
            porcentaje = min(100, round(lote_num / total_lotes * 100))
            elapsed = time.time() - t0
            print(f"  Lote {lote_num}/{total_lotes} ({porcentaje}%) — {elapsed:.0f}s transcurridos")

        elapsed_mes = time.time() - t0
        total_filas_cargadas += total_filas
        print(f"[OK] {archivo.name} — {total_filas:,} filas en {elapsed_mes:.1f}s")

    elapsed_total = time.time() - t0_total
    print(f"\n[OK] fact_viajes completa — {total_filas_cargadas:,} filas "
          f"en {elapsed_total:.1f}s ({elapsed_total/60:.1f} minutos)")

# ─────────────────────────────────────────────────────────────────────────────
# VERIFICACIÓN FINAL
# ─────────────────────────────────────────────────────────────────────────────

def verificar_conteos():
    """Imprime el conteo de filas de cada tabla."""
    tablas = [
        "dim_tiempo", "dim_zona", "dim_proveedor",
        "dim_metodo_pago", "dim_tarifa_pago", "fact_viajes"
    ]
    print("\n[INFO] Verificando conteos en PostgreSQL:")
    for tabla in tablas:
        resultado = ejecutar_sql(f"SELECT COUNT(*) FROM {tabla};")
        lineas = resultado.strip().split("\n")
        conteo = lineas[2].strip() if len(lineas) > 2 else "?"
        print(f"  {tabla:<20} {conteo:>15} filas")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("LOAD2.PY — NYC Taxi Data Warehouse (via Docker)")
    print("=" * 60)

    verificar_conexion()
    limpiar_tablas()

    # Cargar dimensiones (orden importa por las FK)
    print("\n[FASE 1] Cargando dimensiones...")
    cargar_dimension("dim_tiempo", "dim_tiempo", [
        "tiempo_id", "fecha", "dia", "mes",
        "trimestre", "anio", "dia_semana", "es_fin_de_semana"
    ])
    cargar_dimension("dim_zona", "dim_zona", [
        "zona_id", "location_id", "zone",
        "borough", "shape_area", "shape_leng"
    ])
    cargar_dimension("dim_proveedor", "dim_proveedor", [
        "proveedor_id", "vendor_id", "vendor_nombre",
        "store_and_fwd_flag", "tipo_almacenamiento"
    ])
    cargar_dimension("dim_metodo_pago", "dim_metodo_pago", [
        "id_metodo_pago", "payment_type", "payment_descripcion"
    ])
    cargar_dimension("dim_tarifa_pago", "dim_tarifa_pago", [
    "id_tarifa", "ratecode_id", "ratecode_descripcion"
    ])

    # Cargar fact_viajes mes por mes
    print("\n[FASE 2] Cargando fact_viajes (mes por mes)...")
    cargar_fact_viajes()

    # Verificar conteos finales
    verificar_conteos()

    print("\n" + "=" * 60)
    print("Carga completa. Siguiente paso: conectar Power BI / Tableau")
    print("=" * 60)