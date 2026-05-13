import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────────────────────────────────────
STAGING_INPUT  = Path("staging")
STAGING_OUTPUT = Path("staging")

# Nombre correcto del archivo de zonas que deja extract.py
ZONAS_PARQUET  = Path("staging/zonas_parquet.parquet")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 1 — LIMPIEZA (por archivo, no todo junto)
# ─────────────────────────────────────────────────────────────────────────────

def limpiar_mes(df):
    """
    Aplica todas las reglas de calidad a un DataFrame de un mes.
    Se llama una vez por archivo para no juntar todo en memoria.
    """

    # Problema 1: Fechas fuera de rango
    df["tpep_pickup_datetime"]  = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])

    df = df[
        (df["tpep_pickup_datetime"].dt.year == 2025) &
        (df["tpep_dropoff_datetime"].dt.year == 2025)
    ]

    # Problema 2: Valores negativos en campos monetarios
    campos_monetarios = [
        "fare_amount", "tip_amount", "total_amount",
        "tolls_amount", "extra", "mta_tax",
        "improvement_surcharge", "congestion_surcharge"
    ]
    for campo in campos_monetarios:
        if campo in df.columns:
            df = df[df[campo] >= 0]

    # Problema 3: passenger_count debe ser entero positivo
    df["passenger_count"] = pd.to_numeric(df["passenger_count"], errors="coerce")
    df = df[df["passenger_count"] > 0]
    df["passenger_count"] = df["passenger_count"].astype(int)

    # Problema 4: Nulos
    columnas_relleno_cero = [
        "congestion_surcharge", "Airport_fee",
        "cbd_congestion_fee", "tolls_amount"
    ]
    for col in columnas_relleno_cero:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    df["RatecodeID"]        = df["RatecodeID"].fillna(99)
    df["store_and_fwd_flag"] = df["store_and_fwd_flag"].fillna("N")

    # Problema 5: Duplicados
    df = df.drop_duplicates()

    # Estandarizar nombres de columnas a minúsculas
    df.columns = [c.lower() for c in df.columns]

    return df


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2 — CONSTRUIR DIMENSIONES
# Las dimensiones se construyen una sola vez con todos los meses
# pero leyendo un mes a la vez para no llenar la memoria
# ─────────────────────────────────────────────────────────────────────────────

def construir_dimensiones():
    """
    Lee los archivos mes por mes para extraer valores únicos
    necesarios para las dimensiones, sin unirlos todos en memoria.
    """
    archivos = sorted(STAGING_INPUT.glob("tripdata_2025-*.parquet"))

    if not archivos:
        raise FileNotFoundError(
            "No se encontraron archivos en staging/. "
            "Ejecuta primero: python etl/extract.py"
        )

    print(f"[INFO] Archivos encontrados: {len(archivos)}")

    # Acumuladores para valores únicos de dimensiones
    fechas_unicas      = set()
    combinaciones_prov = set()

    for archivo in archivos:
        print(f"  Leyendo {archivo.name} para dimensiones...")
        df = pd.read_parquet(archivo)
        df = limpiar_mes(df)

        # Acumular fechas únicas para dim_tiempo
        fechas_unicas.update(df["tpep_pickup_datetime"].dt.date.unique())

        # Acumular combinaciones únicas para dim_proveedor
        for row in df[["vendorid", "store_and_fwd_flag"]].drop_duplicates().itertuples(index=False):
            combinaciones_prov.add((row.vendorid, row.store_and_fwd_flag))

    # ── dim_tiempo ────────────────────────────────────────────────────────────
    print("[INFO] Construyendo dim_tiempo...")
    fechas_dt = pd.to_datetime(sorted(fechas_unicas))
    dim_tiempo = pd.DataFrame({
        "tiempo_id"        : range(1, len(fechas_dt) + 1),
        "fecha"            : fechas_dt.date,
        "dia"              : fechas_dt.day.astype("int16"),
        "mes"              : fechas_dt.month.astype("int16"),
        "trimestre"        : fechas_dt.quarter.astype("int16"),
        "anio"             : fechas_dt.year.astype("int16"),
        "dia_semana"       : fechas_dt.day_name(),
        "es_fin_de_semana" : fechas_dt.dayofweek >= 5
    })
    print(f"[OK] dim_tiempo: {len(dim_tiempo):,} filas")

    # ── dim_zona ──────────────────────────────────────────────────────────────
    print("[INFO] Construyendo dim_zona...")
    if ZONAS_PARQUET.exists():
        zonas = pd.read_parquet(ZONAS_PARQUET)
    else:
        print("[WARN] zonas_parquet.parquet no encontrado. Usando zonas vacías.")
        zonas = pd.DataFrame(columns=["LocationID","zone","borough","Shape_Area","Shape_Leng"])

    dim_zona = pd.DataFrame({
        "zona_id"    : range(1, len(zonas) + 1),
        "location_id": zonas["LocationID"].values,
        "zone"       : zonas["zone"].values,
        "borough"    : zonas["borough"].values,
        "shape_area" : pd.to_numeric(zonas["Shape_Area"], errors="coerce").fillna(0).values,
        "shape_leng" : pd.to_numeric(zonas["Shape_Leng"], errors="coerce").fillna(0).values,
    })
    print(f"[OK] dim_zona: {len(dim_zona):,} filas")

    # ── dim_proveedor ─────────────────────────────────────────────────────────
    print("[INFO] Construyendo dim_proveedor...")
    nombres_vendor = {
        1: "Creative Mobile Technologies LLC",
        2: "Curb Mobility LLC",
        6: "Myle Technologies Inc",
        7: "Helix"
    }
    tipo_almacenamiento = {
        "Y": "Viaje almacenado y reenviado",
        "N": "Envio directo en tiempo real"
    }
    combinaciones_prov = sorted(combinaciones_prov)
    dim_proveedor = pd.DataFrame({
        "proveedor_id"       : range(1, len(combinaciones_prov) + 1),
        "vendor_id"          : [int(c[0]) for c in combinaciones_prov],
        "vendor_nombre"      : [nombres_vendor.get(c[0], "Desconocido") for c in combinaciones_prov],
        "store_and_fwd_flag" : [c[1] for c in combinaciones_prov],
        "tipo_almacenamiento": [tipo_almacenamiento.get(c[1], "Desconocido") for c in combinaciones_prov],
    })
    print(f"[OK] dim_proveedor: {len(dim_proveedor):,} filas")

    # ── dim_metodo_pago ───────────────────────────────────────────────────────
    print("[INFO] Construyendo dim_metodo_pago...")
    dim_metodo_pago = pd.DataFrame({
        "id_metodo_pago"     : range(1, 8),
        "payment_type"       : [0, 1, 2, 3, 4, 5, 6],
        "payment_descripcion": [
            "Tarifa flexible", "Tarjeta de credito", "Efectivo",
            "Sin cargo", "Disputa", "Desconocido", "Viaje anulado"
        ]
    })
    print(f"[OK] dim_metodo_pago: {len(dim_metodo_pago):,} filas")

    # ── dim_tarifa_pago ───────────────────────────────────────────────────────
    print("[INFO] Construyendo dim_tarifa_pago...")
    dim_tarifa_pago = pd.DataFrame({
        "ratecode_id"         : [1, 2, 3, 4, 5, 6, 99],
        "ratecode_descripcion": [
            "Tarifa estandar", "JFK tarifa fija",
            "Newark tarifa especial", "Nassau o Westchester",
            "Tarifa negociada", "Viaje en grupo", "Desconocido"
        ]
    })
   # dim_tarifa_pago.insert(0, "id_tarifa", range(1, len(dim_tarifa_pago) + 1))
    #print(f"[OK] dim_tarifa_pago: {len(dim_tarifa_pago):,} filas")

    return dim_tiempo, dim_zona, dim_proveedor, dim_metodo_pago, dim_tarifa_pago


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3 — CONSTRUIR FACT_VIAJES (mes por mes)
# ─────────────────────────────────────────────────────────────────────────────

def construir_fact_viajes(dim_tiempo, dim_zona, dim_proveedor,
                           dim_metodo_pago, dim_tarifa_pago):
    """
    Construye fact_viajes procesando un mes a la vez para no
    agotar la memoria RAM. Guarda un parquet por mes en staging.
    """

    # Mapas de lookup
    mapa_tiempo = dict(zip(
        pd.to_datetime(dim_tiempo["fecha"]),
        dim_tiempo["tiempo_id"]
    ))
    mapa_zona = dict(zip(
        dim_zona["location_id"],
        dim_zona["zona_id"]
    ))
    mapa_proveedor = {
        (row.vendor_id, row.store_and_fwd_flag): row.proveedor_id
        for row in dim_proveedor.itertuples()
    }
    mapa_metodo_pago = dict(zip(
        dim_metodo_pago["payment_type"],
        dim_metodo_pago["id_metodo_pago"]
    ))
    mapa_tarifa = dict(zip(
        dim_tarifa_pago["ratecode_id"],
        dim_tarifa_pago["id_tarifa"]
    ))

    archivos = sorted(STAGING_INPUT.glob("tripdata_2025-*.parquet"))
    total_filas = 0

    for archivo in archivos:
        print(f"  Procesando {archivo.name}...")
        df = pd.read_parquet(archivo)
        df = limpiar_mes(df)

        pickup_fecha = df["tpep_pickup_datetime"].dt.normalize()

        fact = pd.DataFrame({
            "tiempo_id"             : pickup_fecha.map(mapa_tiempo),
            "zona_pickup_id"        : df["pulocationid"].map(mapa_zona),
            "zona_dropoff_id"       : df["dolocationid"].map(mapa_zona),
            "id_metodo_pago"        : df["payment_type"].map(mapa_metodo_pago),
            "proveedor_id"          : [
                mapa_proveedor.get((row.vendorid, row.store_and_fwd_flag))
                for row in df[["vendorid", "store_and_fwd_flag"]].itertuples(index=False)
            ],
            "ratecode_id"           : df["ratecodeid"].map(mapa_tarifa),
            "pickup_datetime"       : df["tpep_pickup_datetime"],
            "dropoff_datetime"      : df["tpep_dropoff_datetime"],
            "passenger_count"       : df["passenger_count"],
            "trip_distance"         : df["trip_distance"],
            "fare_amount"           : df["fare_amount"],
            "extra"                 : df["extra"],
            "mta_tax"               : df["mta_tax"],
            "tip_amount"            : df["tip_amount"],
            "tolls_amount"          : df["tolls_amount"],
            "improvement_surcharge" : df["improvement_surcharge"],
            "congestion_surcharge"  : df["congestion_surcharge"],
            "airport_fee"           : df["airport_fee"],
            "cbd_congestion_fee"    : df["cbd_congestion_fee"],
            "total_amount"          : df["total_amount"],
        })

        # Eliminar filas donde alguna FK quedó sin resolver
        antes = len(fact)
        fact = fact.dropna(subset=["tiempo_id", "zona_pickup_id", "zona_dropoff_id"])
        descartadas = antes - len(fact)
        if descartadas > 0:
            print(f"  [WARN] {descartadas:,} filas descartadas por FK sin resolver")

        # Guardar un parquet por mes
        nombre_mes = archivo.stem.replace("tripdata_", "fact_viajes_")
        ruta_salida = STAGING_OUTPUT / f"{nombre_mes}.parquet"
        fact.to_parquet(ruta_salida, index=False)
        size_mb = ruta_salida.stat().st_size / 1e6
        total_filas += len(fact)
        print(f"  [GUARDADO] {ruta_salida.name} — {len(fact):,} filas — {size_mb:.1f} MB")

    print(f"[OK] fact_viajes total: {total_filas:,} filas en {len(archivos)} archivos")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4 — GUARDAR DIMENSIONES EN STAGING
# ─────────────────────────────────────────────────────────────────────────────

def guardar(df, nombre):
    """Guarda un DataFrame como Parquet en staging."""
    ruta = STAGING_OUTPUT / f"{nombre}.parquet"
    df.to_parquet(ruta, index=False)
    size_mb = ruta.stat().st_size / 1e6
    print(f"[GUARDADO] {ruta.name} — {size_mb:.1f} MB")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("TRANSFORM.PY — NYC Taxi Data Warehouse")
    print("=" * 60)

    # Paso 1 y 2: construir dimensiones leyendo mes por mes
    print("\n[FASE 1] Construyendo dimensiones...")
    dim_tiempo, dim_zona, dim_proveedor, dim_metodo_pago, dim_tarifa_pago = construir_dimensiones()

    # Guardar dimensiones
    print("\n[INFO] Guardando dimensiones en staging/...")
    guardar(dim_tiempo,      "dim_tiempo")
    guardar(dim_zona,        "dim_zona")
    guardar(dim_proveedor,   "dim_proveedor")
    guardar(dim_metodo_pago, "dim_metodo_pago")
    guardar(dim_tarifa_pago, "dim_tarifa_pago")

    # Paso 3: construir fact_viajes mes por mes
    print("\n[FASE 2] Construyendo fact_viajes (mes por mes)...")
    construir_fact_viajes(
        dim_tiempo, dim_zona, dim_proveedor,
        dim_metodo_pago, dim_tarifa_pago
    )

    print("\n" + "=" * 60)
    print("Transform completo. Siguiente paso: python etl/load.py")
    print("=" * 60)
