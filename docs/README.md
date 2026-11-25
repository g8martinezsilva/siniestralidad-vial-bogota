# Documento del proyecto

`main.tex` es el informe del proyecto. La versión que se entrega es la de este repositorio.

## Compilar

```bash
cd docs
pdflatex main.tex
pdflatex main.tex   # segunda pasada para referencias
```

La portada usa `escudo.png` (escudo de la universidad), que debe estar en esta misma carpeta.

## Informe

La numeración de capítulos, apartados, tablas y figuras se genera en LaTeX.
Por ejemplo, las figuras del capítulo Desarrollo se numeran 5.1, 5.2, etc.
Las citas autor-año se gestionan con `natbib` y la bibliografía de `main.tex`.

Las figuras que utiliza el documento se guardan en `docs/figuras/`.
Para regenerarlas, ejecutar desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m siniestralidad.describir
.\.venv\Scripts\python.exe -m siniestralidad.contrastar
.\.venv\Scripts\python.exe -m siniestralidad.agrupar
.\.venv\Scripts\python.exe -m siniestralidad.asociar
Copy-Item reports\figuras\*.png docs\figuras\
Copy-Item reports\figuras\*.html docs\figuras\
```

Los mapas descargan teselas de OpenStreetMap en la primera ejecución y
las reutilizan desde `data/external/cache_cartografia/` (sin versionar).
La descarga requiere conexión; el LaTeX compila con los PNG ya incluidos.
La atribución del fondo está incorporada a los mapas y debe conservarse.
Verde, amarillo, naranja y rojo expresan magnitudes; no equivalen por sí
solos a niveles de riesgo. En las barras de gravedad, los colores indican
solo daños, heridos y muertos, respectivamente.
