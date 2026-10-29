# Datos

## Fuente

**Base Anuario de Siniestralidad 2024**, publicada por la Secretaría Distrital de Movilidad (SIMUR) en el portal de datos abiertos de Bogotá:

- Página del recurso: <https://datosabiertos.bogota.gov.co/dataset/anuario-siniestralidad/resource/35168f38-f3b3-4411-a0c5-545f3ec8869e>
- Archivo: `base-anuario-de-siniestralidad-2024.xlsx` (≈ 127 MB)

El archivo trae tres hojas principales (siniestros, vehículos y actor vial) y un diccionario de datos.

## Cómo dejarla lista

1. Descarga el archivo desde el enlace de arriba. También sirve un `.zip` con las hojas exportadas a CSV: `siniestros.csv`, `vehiculos.csv` y `actores.csv`.
2. Guárdalo, sin cambiarle el nombre, en `data/raw/base-anuario-de-siniestralidad-2024.xlsx`.
3. Ejecuta `python -m siniestralidad.preparar` desde la raíz del repositorio.

La primera lectura del Excel tarda unos minutos; el programa guarda una copia en `data/raw/cache/` para que las siguientes sean rápidas.

## Carpetas

| Carpeta | Contenido | ¿Se sube a GitHub? |
|---|---|---|
| `raw/` | Base original del SIMUR, sin modificar | No (pesa mucho y es pública) |
| `processed/` | Bases generadas por el programa | No (se regeneran) |

## Columnas de la hoja de siniestros

Según el diccionario publicado, todas vienen como texto:

- **Identificación y ubicación:** `Codigo_Accidente`, `Formulario`, `Longitud`, `Latitud`, `Direccion`, `Localidad`
- **Fecha y hora:** `Fecha_Acc`, `AA_Acc`, `MM_Acc`, `DD_Mes_Acc`, `Dia_Semana_Acc`, `Hora_Acc`, `Min_Acc`
- **Evento:** `Clase_Acc`, `Elemento_Choque`, `Tipo_Objeto_Fijo`, `Gravedad_Indicador_Tradicional`, `Gravedad_indicador_30d`
- **Indicadores `Con_*`:** `Con_Bicicleta`, `Con_Carga`, `Con_Embriaguez`, `Con_Huecos`, `Con_Menores`, `Con_Moto`, `Con_Peaton`, `Con_Persona_Mayor`, `Con_Rutas`, `Con_Tpi`, `Con_Tpp`, `Con_Velocidad`, `Con_Sitp`, `Con_Troncal`, `Con_Alimentador`, `Con_Zonal`, `Con_Provisional`, `Con_Articulado`, `Con_Biarticulado`, `Con_Padron_Dual`, `Con_Servicio_Especial`, `Con_Taxi`

> La base **no trae una columna de corredor**; el programa lo deduce de `Direccion` (ver `src/siniestralidad/corredores.py`).
