import time
import requests
from tqdm import tqdm
from pathlib import Path

# Configuracion para descargar a staging ────────────────────────────────────────────────
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-{mes:02d}.parquet"
BASE_URL_ZONE = "https://data.source.coop/cholmes/nyc-taxi-zones/taxi_zones_4326.parquet"
MESES = list(range(1,13))

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT = BASE_DIR/"staging"
CHUNK_BYTES = 8 * 1024 * 1024
TIMEOUT = 180

# Descarga ───────────────────────────────────────────────────────────────────────────────────────
def descargar_mes(mes):
    '''
    Descarga el dataset del sitio oficia de NYC Taxi Trips (TLC) por mes.

    mes: int
    '''
    url = BASE_URL.format(mes=mes)
    destino = OUTPUT/f"tripdata_2025-{mes:02d}.parquet"

    try:
        r = requests.get(url, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.HTTPError:
        print(f"[SKIP] Mes {mes:02d} no disponible en TLC.")
        return None
    except requests.ConnectionError as e:
        print(f"[ERROR] Sin conexion: {e}")
        raise

    total_bytes = int(r.headers.get("content-length", 0))
    t0 = time.perf_counter()

    with open(destino, 'wb') as archivo, tqdm(
        total = total_bytes, unit="B", unit_scale=True,
        unit_divisor = 1024, desc = destino.name
    ) as bar:
        for chunk in r.iter_content(chunk_size = CHUNK_BYTES):
            if chunk:
                archivo.write(chunk)
                bar.update(len(chunk))

    elapsed = time.perf_counter() - t0
    size_mb = destino.stat().st_size / 1e6
    print(f"[OK] {destino.name}: {size_mb:.1f} MB en {elapsed:.1f}s")
    return destino

def descargar_zona():
    '''
    Descarga la base de zonas utlizadas en el dataset tripdata.
    '''
    url = BASE_URL_ZONE
    destino = OUTPUT/f"zonas_parquet.parquet"

    try:
        r = requests.get(url, stream=True, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.ConnectionError as e:
        print(f"[ERROR] Sin conexion: {e}")
        raise
    
    total_bytes = int(r.headers.get("content-length", 0))
    t0 = time.perf_counter()

    with open(destino, 'wb') as archivo, tqdm(
        total = total_bytes, unit="B", unit_scale=True,
        unit_divisor = 1024, desc = destino.name
    ) as bar:
        archivo.write(r.content)
        bar.update(len((r.content)))
    
    elapsed = time.perf_counter() - t0
    size_mb = destino.stat().st_size / 1e6

    print(f"[OK] {destino.name}: {size_mb:.1f} MB en {elapsed:.1f}s")

    return destino


if __name__ == "__main__":

    t0 = time.perf_counter()

    print("=" * 60)
    print("EXTRACT — NYC Taxi Trips (TLC)")
    print("=" * 60)

    for mes in MESES:
        ruta = descargar_mes(mes)
    
    zonas = descargar_zona()

    print(f"\n{'=' * 60}")
    print(f"[INFO] Archivos disponibles en {OUTPUT}:")

    t_final = time.perf_counter() - t0
    print(f"[INFO] Tiempo de extracion: {t_final:.1f}s")