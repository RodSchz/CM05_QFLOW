#!/usr/bin/env python3
"""Genera notebooks/CM05_QFLOW.ipynb (fuente editable del notebook).
Uso: python3 tools/make_notebook.py"""
import nbformat as nbf
from pathlib import Path

REPO = "RodSchz/CM05_QFLOW"
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
cells = []

cells.append(md(f"""# CM05_QFLOW — de Verilog a GDS en el proceso CIDESI_CM05

<a href="https://colab.research.google.com/github/{REPO}/blob/main/notebooks/CM05_QFLOW.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

Este notebook lleva un diseño digital escrito en **Verilog** hasta un **layout GDS** del proceso
**CIDESI_CM05** (CMOS, λ = 2.5 µm, 2 metales, 1 polisilicio) usando **qflow**:

1. **Síntesis** con yosys a la biblioteca de celdas `cm05` (celdas OSU adaptadas a CM05).
2. **Colocación** con graywolf y **ruteo** en 2 metales con qrouter.
3. **LVS** con magic + netgen (layout contra netlist sintetizado).
4. **Legalización post-ruteo**: aleja las vías de los bordes de poly/activo (regla 8.5 de CM05, proceso sin planarización).
5. **DRC** con el deck oficial de CIDESI_CM05 en KLayout.

Ejecuta las celdas en orden (**Entorno de ejecución → Ejecutar todas**). La instalación tarda unos minutos la primera vez."""))

cells.append(md("## 1. Instalación\nDescarga este repositorio y el PDK `CIDESI_CM05` (para el deck DRC) e instala yosys, graywolf, qrouter, magic, netgen, qflow y KLayout."))
cells.append(code("""import os, pathlib
BASE = pathlib.Path('/content') if pathlib.Path('/content').exists() else pathlib.Path.home() / 'cm05_work'
BASE.mkdir(parents=True, exist_ok=True)
REPO_DIR = BASE / 'CM05_QFLOW'
PDK_DIR = BASE / 'CIDESI_CM05'
PREFIX = '/opt/cm05_eda'
os.environ['BASE'] = str(BASE)
os.environ['REPO_DIR'] = str(REPO_DIR)
os.environ['PDK_DIR'] = str(PDK_DIR)
os.environ['PATH'] = f"{PREFIX}/bin:{PREFIX}/shims:" + os.environ['PATH']
print('Carpeta de trabajo:', BASE)"""))
cells.append(code(f"""%%bash
set -e
[ -d "$REPO_DIR" ] || git clone -q --depth 1 https://github.com/{REPO} "$REPO_DIR"
[ -d "$PDK_DIR" ]  || git clone -q --depth 1 https://github.com/RodSchz/CIDESI_CM05 "$PDK_DIR"
bash "$REPO_DIR/scripts/install_tools.sh" 2>&1 | grep -E "^==|binarios|compilando|Listo|ERROR|KLayout [0-9]"
for t in yosys graywolf qrouter magic netgen qflow klayout; do printf "%-9s %s\\n" $t "$(command -v $t || echo FALTA)"; done"""))

cells.append(md("""## 2. Tu diseño en Verilog

Escribe tu módulo en `VERILOG` y pon su nombre en `MODULO`, o elige uno de los ejemplos con `EJEMPLO`
(`'counter'`, `'lfsr8'`, `'alu4'`, `'pwm8'`).

**Restricciones de la biblioteca `cm05`:**
- Solo **reset síncrono** (`always @(posedge clk) if (rst) ...`): el flip-flop con set/reset asíncrono (DFFSR) no está disponible porque viola la regla 8.5 de CM05.
- XOR/XNOR, sumadores completos (FAX1/HAX1) y latches tampoco están; yosys los arma con compuertas simples.
- Celdas disponibles: INV, BUF, NAND2/3, NOR2/3, AND2, OR2, AOI21/22, OAI21/22, MUX2, TBUF y DFFPOSX1."""))
cells.append(code("""EJEMPLO = 'counter'      # None para usar tu propio código de abajo

MODULO = 'mi_diseno'
VERILOG = r'''
// Ejemplo: contador de 4 bits con reset sincrono
module mi_diseno (input clk, input rst, input en, output reg [3:0] q);
  always @(posedge clk)
    if (rst)     q <= 4'd0;
    else if (en) q <= q + 4'd1;
endmodule
'''

if EJEMPLO:
    MODULO = EJEMPLO
    VERILOG = (REPO_DIR / 'examples' / EJEMPLO / f'{EJEMPLO}.v').read_text()

WORK = BASE / 'work' / MODULO
(WORK / 'source').mkdir(parents=True, exist_ok=True)
(WORK / 'source' / f'{MODULO}.v').write_text(VERILOG)
os.environ['MODULO'] = MODULO
os.environ['WORK'] = str(WORK)
print(VERILOG)"""))

cells.append(md("""## 3. Flujo completo
Si el ruteo no cierra, el script reintenta con menor densidad de colocación (0.7 → 0.5 → 0.4 → 0.3):
con solo dos metales el ruteo necesita espacio libre entre celdas."""))
cells.append(code("""%%bash
DECK="$PDK_DIR/tech/CIDESI_CM05/drc/drc.lydrc"
bash "$REPO_DIR/scripts/cm05_flow.sh" "$MODULO" "$WORK" "$DECK" """))

cells.append(md("## 4. Resultados"))
cells.append(code("""import re, subprocess, klayout.db as kdb
synth = (WORK / 'log' / 'synth.log').read_text(errors='ignore')
stats = re.findall(r'Number of cells:\\s+(\\d+)\\n(.*?)\\n\\n', synth, re.S)
if stats:                      # la ultima estadistica es la del mapeo final a celdas cm05
    total, body = stats[-1]
    print('Celdas tras la síntesis:', total)
    for name, n in re.findall(r'^\\s+([A-Z][A-Z0-9_]+)\\s+(\\d+)$', body, re.M):
        print(f'   {name:10s} {n}')
gds = WORK / f'{MODULO}_cm05.gds'
ly = kdb.Layout(); ly.read(str(gds))
bb = ly.top_cell().dbbox()
print(f'\\nGDS: {gds}')
print(f'Tamaño: {bb.width():.0f} µm × {bb.height():.0f} µm  ({bb.width()*bb.height()/1e6:.2f} mm²)')
print('\\nDRC (deck oficial CIDESI_CM05):')
print(subprocess.run(['python3', '-I', str(REPO_DIR / 'scripts' / 'rdb_summary.py'),
                      str(WORK / f'{MODULO}_cm05_drc.lyrdb')], capture_output=True, text=True).stdout)"""))

cells.append(md("""## 5. Visualización del layout
`ZOOM = None` muestra el chip completo; para acercarte usa `ZOOM = (x1, y1, x2, y2)` en µm."""))
cells.append(code("""import klayout.lay as klay
from IPython.display import Image, display
ZOOM = None          # p. ej. (0, 0, 300, 300)

lv = klay.LayoutView()
lv.load_layout(str(gds), True)
lv.load_layer_props(str(PDK_DIR / 'tech' / 'CIDESI_CM05' / 'CIDESI_CM05.lyp'))
lv.max_hier()
lv.set_config('background-color', '#ffffff')
lv.set_config('grid-visible', 'false')
if ZOOM:
    lv.zoom_box(kdb.DBox(*ZOOM))
else:
    lv.zoom_fit()
png = WORK / f'{MODULO}_cm05.png'
lv.save_image(str(png), 1400, 1050)
display(Image(str(png)))"""))

cells.append(md("## 6. Descargar el GDS"))
cells.append(code("""try:
    from google.colab import files
    files.download(str(gds))
except ImportError:
    print('Fuera de Colab: el GDS está en', gds)"""))

cells.append(md("""## Notas
- **Liberty aproximado:** los tiempos y capacitancias de la biblioteca vienen de AMI C5 (0.5 µm); sirven para que yosys mapee la lógica, no para estimar el desempeño en CM05.
- **Áreas:** las celdas se ensancharon donde fue necesario para que cada pin admita una vía legal (proceso sin planarización), así que los diseños son más grandes que una versión directa escalada de OSU.
- **Archivos intermedios:** en `WORK` quedan el netlist sintetizado (`*_mapped.v`), el DEF ruteado, los logs de cada etapa (`log/`) y el reporte DRC (`*_cm05_drc.lyrdb`, se abre en KLayout)."""))

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "colab": {"provenance": [], "toc_visible": True},
    "kernelspec": {"name": "python3", "display_name": "Python 3"},
    "language_info": {"name": "python"}})
out = Path(__file__).resolve().parent.parent / "notebooks" / "CM05_QFLOW.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print("escrito:", out)
