"""Rutas y parámetros del estudio.

Todo lo que se pueda querer ajustar al ver la base real vive aquí, para no
tener que tocar la lógica de los demás módulos.
"""

from pathlib import Path

# --- Rutas ---------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"
REPORTS = RAIZ / "reports"
TABLAS = REPORTS / "tablas"
FIGURAS = REPORTS / "figuras"

# Base del Anuario de Siniestralidad 2024 (SIMUR / datos abiertos Bogotá).
ARCHIVO_ANUARIO = RAW / "base-anuario-de-siniestralidad-2024.xlsx"
URL_ANUARIO = (
    "https://datosabiertos.bogota.gov.co/dataset/8aa2f79c-5d32-4e6a-8eb3-a5af0ac4c172/"
    "resource/35168f38-f3b3-4411-a0c5-545f3ec8869e/download/"
    "base-anuario-de-siniestralidad-2024.xlsx"
)

# Longitud de cada corredor (km), necesaria para H1.
ARCHIVO_LONGITUDES = EXTERNAL / "longitudes_corredores.csv"

# --- Población -----------------------------------------------------------
ANIO = 2024
N_CORREDORES = 10
# Si es False, un siniestro solo cuenta para la vía principal de la dirección.
CORREDOR_AMBAS_VIAS = True

# Caja que contiene el área urbana de Bogotá (grados WGS84). Sirve para
# descartar coordenadas fuera de la ciudad, no como límite exacto.
BOGOTA_BBOX = {
    "lat_min": 3.70,
    "lat_max": 4.85,
    "lon_min": -74.45,
    "lon_max": -73.95,
}

# --- Columnas de la hoja de siniestros (diccionario de datos abiertos) ---
COL_ID = "Codigo_Accidente"
COL_FECHA = "Fecha_Acc"
COL_HORA = "Hora_Acc"
COL_MINUTO = "Min_Acc"
COL_LAT = "Latitud"
COL_LON = "Longitud"
COL_DIRECCION = "Direccion"
COL_LOCALIDAD = "Localidad"
COL_CLASE = "Clase_Acc"
COL_GRAVEDAD = "Gravedad_Indicador_Tradicional"
COL_MOTO = "Con_Moto"

# Variables clave para el indicador "menos del 5 % de nulos" del OE1.
VARIABLES_CLAVE = ["corredor", "fecha", "hora", "gravedad", "con_moto"]

# --- Variables derivadas -------------------------------------------------
# Franjas horarias del documento (sección Desarrollo): [inicio, fin).
FRANJAS_BORDES = [0, 6, 10, 16, 20, 24]
FRANJAS = ["madrugada", "manana", "mediodia", "tarde", "noche"]

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

# Gravedad ordinal: se normaliza el texto y se busca la palabra clave.
GRAVEDAD_ORDEN = ["solo danos", "con heridos", "con muertos"]
GRAVEDAD_PALABRAS = {
    "muert": "con muertos",
    "herid": "con heridos",
    "dan": "solo danos",
}
