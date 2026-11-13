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

0. **Simulación RTL** de tu Verilog con Icarus Verilog y un testbench.
1. **Síntesis** con yosys a la biblioteca de celdas `cm05` (celdas OSU adaptadas a CM05).
2. **Colocación** con graywolf y **ruteo** en 2 metales con qrouter.
3. **LVS** con magic + netgen (layout contra netlist sintetizado).
4. **Legalización post-ruteo**: aleja las vías de los bordes de poly/activo (regla 8.5 de CM05, proceso sin planarización).
5. **DRC** con el deck oficial de CIDESI_CM05 en KLayout.
6. **Simulación post-layout**: el mismo testbench sobre el netlist extraído del layout ruteado, comparado contra la simulación RTL.

Ejecuta las celdas en orden (**Entorno de ejecución → Ejecutar todas**). La instalación tarda unos minutos la primera vez."""))

cells.append(md("## 1. Instalación\nDescarga este repositorio y el PDK `CIDESI_CM05` (para el deck DRC) e instala Icarus Verilog, yosys, graywolf, qrouter, magic, netgen, qflow y KLayout."))
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
for t in iverilog yosys graywolf qrouter magic netgen qflow klayout; do printf "%-9s %s\\n" $t "$(command -v $t || echo FALTA)"; done"""))

cells.append(md("""## 2. Tu diseño y su testbench

El diseño y su testbench son **archivos `.v`** en la carpeta `diseno/` (panel de archivos 📁 a la izquierda).
Al ejecutar la celda aparecen abajo en un **editor con resaltado de Verilog**: edítalos ahí y pulsa
**Guardar** (o Ctrl+S con el cursor dentro del editor). Las celdas siguientes siempre leen la versión guardada.
(El visor de archivos de Colab también los abre con doble clic, pero sin colores.)

- `MODULO` puede ser un ejemplo (`'counter'`, `'lfsr8'`, `'alu4'`, `'pwm8'`, con testbench autoverificable)
  o el nombre de tu módulo: si `diseno/<MODULO>.v` no existe, se crea una plantilla.
- También puedes **subir tus archivos** a `diseno/` arrastrándolos al panel de archivos
  (`<MODULO>.v` y `<MODULO>_tb.v`).
- Tus cambios no se sobrescriben al volver a ejecutar la celda; `RESTAURAR = True` vuelve a copiar el ejemplo.

**El testbench** debe ser el módulo superior, escribir las ondas con `$dumpfile("sim.vcd")` y reportar con
`$display`; si imprime una línea que empiece con `RESULTADO:`, el notebook la muestra como resumen.
Cambia las entradas y lee las salidas en el **flanco de bajada** del reloj (`@(negedge clk)`): si una entrada
cambia en el mismo instante que el flanco de subida, RTL y post-layout pueden resolver el empate distinto.

**Restricciones de la biblioteca `cm05`:**
- Solo **reset síncrono** (`always @(posedge clk) if (rst) ...`): el flip-flop con set/reset asíncrono (DFFSR) no está disponible porque viola la regla 8.5 de CM05.
- XOR/XNOR, sumadores completos (FAX1/HAX1) y latches tampoco están; yosys los arma con compuertas simples.
- Celdas disponibles: INV, BUF, NAND2/3, NOR2/3, AND2, OR2, AOI21/22, OAI21/22, MUX2, TBUF y DFFPOSX1."""))
cells.append(code('''MODULO = 'counter'      # ejemplo ('counter', 'lfsr8', 'alu4', 'pwm8') o el nombre de tu módulo
RESTAURAR = False       # True: vuelve a copiar el ejemplo encima de tus cambios

import shutil
PLANTILLA_RTL = """// MODULO: contador de 4 bits con reset sincrono (plantilla)
module MODULO (input clk, input rst, input en, output reg [3:0] q);
  always @(posedge clk)
    if (rst)     q <= 4'd0;
    else if (en) q <= q + 4'd1;
endmodule
"""
PLANTILLA_TB = """// Testbench de MODULO (plantilla)
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, en = 1;
  wire [3:0] q;
  MODULO dut (.clk(clk), .rst(rst), .en(en), .q(q));
  always #50 clk = ~clk;                       // 10 MHz
  initial begin
    $dumpfile("sim.vcd"); $dumpvars(0, tb);
    repeat (3) @(negedge clk);                 // cambia entradas en el flanco de bajada
    rst = 0;
    repeat (20) begin @(negedge clk); $display("q=%0d", q); end
    $display("RESULTADO: simulacion terminada");
    $finish;
  end
endmodule
"""

DISENO = BASE / 'diseno'
DISENO.mkdir(exist_ok=True)
RTL_V, TB_V = DISENO / f'{MODULO}.v', DISENO / f'{MODULO}_tb.v'
ejemplo = REPO_DIR / 'examples' / MODULO
for src, dst in ((ejemplo / f'{MODULO}.v', RTL_V), (ejemplo / f'{MODULO}_tb.v', TB_V)):
    if src.exists() and (RESTAURAR or not dst.exists()):
        shutil.copy(src, dst)
if not RTL_V.exists():
    RTL_V.write_text(PLANTILLA_RTL.replace('MODULO', MODULO))
if not TB_V.exists():
    TB_V.write_text(PLANTILLA_TB.replace('MODULO', MODULO))

WORK = BASE / 'work' / MODULO
(WORK / 'source').mkdir(parents=True, exist_ok=True)
os.environ.update(MODULO=MODULO, WORK=str(WORK), DISENO=str(DISENO))

def descargar(*rutas):
    """Descarga archivos al navegador (en Colab); fuera de Colab solo muestra la ruta."""
    try:
        from google.colab import files as colab_files
        for r in rutas:
            colab_files.download(str(r))
    except ImportError:
        print('Fuera de Colab; archivos en:', *map(str, rutas))

import sys
sys.path.insert(0, str(REPO_DIR / 'scripts'))
from verilog_editor import editor
editor(RTL_V)
editor(TB_V)'''))
cells.append(md("""## 3. Simulación RTL
Simula tu Verilog antes de mandarlo a layout. En la gráfica de ondas puedes elegir señales con `SENALES`
(p. ej. `['clk', 'rst', 'q']`; `None` = todas las del testbench) y una ventana de tiempo en ns con `T0`, `T1`.
Con `DESCARGAR_VCD = True` el archivo de ondas (`<modulo>_rtl.vcd`) se descarga solo, para abrirlo en GTKWave."""))
cells.append(code("""%%bash
cp "$DISENO/$MODULO.v" "$WORK/source/" && cp "$DISENO/${MODULO}_tb.v" "$WORK/"
bash "$REPO_DIR/scripts/cm05_sim.sh" "$MODULO" "$WORK" "$WORK/${MODULO}_tb.v" rtl 2>&1 | grep -v "typ expression"
echo "--- primeras lineas de la salida del testbench:"
head -12 "$WORK/sim_rtl/salida.txt"
"""))
cells.append(code("""import sys
sys.path.insert(0, str(REPO_DIR / 'scripts'))
import matplotlib.pyplot as plt
from vcd_plot import plot as ondas
SENALES = None          # p. ej. ['clk', 'rst', 'q']
T0, T1 = 0, 3000        # ventana en ns (None = completa)
DESCARGAR_VCD = True

ondas(str(WORK / 'sim_rtl' / 'sim.vcd'), SENALES, T0, T1)
plt.show()
VCD_RTL = WORK / f'{MODULO}_rtl.vcd'
shutil.copy(WORK / 'sim_rtl' / 'sim.vcd', VCD_RTL)
if DESCARGAR_VCD:
    descargar(VCD_RTL)"""))

cells.append(md("""## 4. Flujo de Verilog a GDS
Si el ruteo no cierra, el script reintenta con menor densidad de colocación (0.7 → 0.5 → 0.4 → 0.3):
con solo dos metales el ruteo necesita espacio libre entre celdas."""))
cells.append(code("""%%bash
cp "$DISENO/$MODULO.v" "$WORK/source/" && cp "$DISENO/${MODULO}_tb.v" "$WORK/"
DECK="$PDK_DIR/tech/CIDESI_CM05/drc/drc.lydrc"
bash "$REPO_DIR/scripts/cm05_flow.sh" "$MODULO" "$WORK" "$DECK" """))

cells.append(md("""## 5. Simulación post-layout
El mismo testbench sobre el netlist que quedó en el layout ruteado (`<modulo>_postroute.v`, con los modelos
de las celdas cm05). Las trazas de texto deben ser **idénticas** a las de la simulación RTL.
La simulación es funcional (sin retardos): los tiempos del liberty son de AMI C5, no de CM05.
Con `DESCARGAR_VCD = True` se descarga `<modulo>_postlayout.vcd`."""))
cells.append(code("""%%bash
cp "$DISENO/${MODULO}_tb.v" "$WORK/"
bash "$REPO_DIR/scripts/cm05_sim.sh" "$MODULO" "$WORK" "$WORK/${MODULO}_tb.v" ambos 2>&1 | grep -v "typ expression"
"""))
cells.append(code("""fig, axs = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
ondas(str(WORK / 'sim_rtl' / 'sim.vcd'), SENALES, T0, T1, ax=axs[0]); axs[0].set_title('RTL')
ondas(str(WORK / 'sim_gate' / 'sim.vcd'), SENALES, T0, T1, ax=axs[1]); axs[1].set_title('Post-layout (compuertas cm05)')
plt.tight_layout(); plt.show()
VCD_GATE = WORK / f'{MODULO}_postlayout.vcd'
shutil.copy(WORK / 'sim_gate' / 'sim.vcd', VCD_GATE)
if DESCARGAR_VCD:
    descargar(VCD_GATE)"""))

cells.append(md("## 6. Resultados del layout"))
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

cells.append(md("""## 7. Visualización del layout
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

cells.append(md("""## 8. Descargar resultados
Un `.zip` con el Verilog y testbench, el GDS, la imagen del layout, los VCD de ambas simulaciones,
el netlist post-ruteo, el reporte DRC (`.lyrdb`, se abre en KLayout) y el log de qflow."""))
cells.append(code("""import zipfile
ZIP = BASE / f'{MODULO}_cm05_resultados.zip'
contenido = [RTL_V, TB_V, gds, png, WORK / f'{MODULO}_rtl.vcd', WORK / f'{MODULO}_postlayout.vcd',
             WORK / f'{MODULO}_postroute.v', WORK / f'{MODULO}_cm05_drc.lyrdb', WORK / 'qflow.log']
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in contenido:
        if f.exists():
            z.write(f, f'{MODULO}_cm05/{f.name}')
print(ZIP, f'({ZIP.stat().st_size/1e6:.1f} MB)')
descargar(ZIP)"""))

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
