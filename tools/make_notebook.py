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

**Cómo usarlo:** ejecuta la instalación (paso 1), ajusta tus opciones en el **formulario de configuración** (paso 2) y
ejecuta el resto en orden (**Entorno de ejecución → Ejecutar todas**). La instalación tarda unos minutos la primera vez."""))

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
# clona, o actualiza si la sesion de Colab ya tenia una copia anterior
for par in "$REPO_DIR https://github.com/{REPO}" "$PDK_DIR https://github.com/RodSchz/CIDESI_CM05"; do
  set -- $par
  if [ -d "$1/.git" ]; then git -C "$1" pull -q --ff-only || echo "AVISO: no se pudo actualizar $1"
  else git clone -q --depth 1 "$2" "$1"; fi
done
echo "CM05_QFLOW: $(git -C "$REPO_DIR" log -1 --format='%h %cd' --date=short)"
bash "$REPO_DIR/scripts/install_tools.sh" 2>&1 | grep -E "^==|binarios|compilando|Listo|ERROR|KLayout [0-9]"
for t in iverilog yosys graywolf qrouter magic netgen qflow klayout; do printf "%-9s %s\\n" $t "$(command -v $t || echo FALTA)"; done"""))

cells.append(md("""## 2. Configuración
Todas las opciones que puedes cambiar están en el formulario de la celda siguiente; los pasos posteriores solo las
usan (cada uno imprime al inicio los valores con que trabaja). **Si cambias algo, vuelve a ejecutar esta celda** y
después el paso que quieras repetir (o *Ejecutar todas*).

| Opción | Qué hace |
|---|---|
| `EJEMPLO` | Diseño de ejemplo del repo, o *subir mis archivos* para usar tu Verilog (paso 3). |
| `DENSIDAD` | Fracción del área ocupada por celdas. *automática* prueba 0.7 → 0.5 → 0.4 → 0.3 hasta que el ruteo cierra (con 2 metales el ruteo necesita espacio libre); un valor fijo hace un solo intento. |
| `ASPECTO` | Proporción **alto/ancho** del chip: 0.4 da un chip ancho y bajo; 2.0, uno alto. |
| `PINES_*` | Pines de E/S de cada lado, separados por comas (`clk, rst`). Un bus sin índice (`q`) incluye todos sus bits; los que no pongas quedan libres. **Con 2 metales usa arriba/abajo**: a los costados compiten con las franjas de alimentación. Todos vacíos = libres (o el `.cel2` que subas). |
| `ORDEN_FIJO` | Marcado: respeta el orden escrito en cada lado; sin marcar, graywolf los permuta para acortar el ruteo. |
| `TAMANO_ETIQUETAS` | Alto (µm) del texto de los pines en el GDS (capas 49/1 y 51/1). En KLayout de escritorio se ve a su tamaño real con *File → Setup → Display → Texts → Font: Stick Font*. |
| `SENALES`, `T0`, `T1` | Señales a graficar (vacío = todas las del testbench) y ventana de tiempo en ns (`T1 = 0` = hasta el final). |
| `ZOOM` | Vacío = chip completo en la vista del layout; `x1, y1, x2, y2` (µm) para acercarte. |"""))
cells.append(code("""#@title Configuración del diseño { display-mode: "form" }
#@markdown ### Diseño
EJEMPLO = 'counter'  #@param ["(subir mis archivos)", "counter", "lfsr8", "alu4", "pwm8"]
#@markdown ### Colocación y ruteo
DENSIDAD = 'automática'  #@param ["automática", "0.8", "0.7", "0.6", "0.5", "0.4", "0.3"]
ASPECTO = 0.75  #@param {type:"slider", min:0.25, max:4, step:0.05}
#@markdown ### Pines (separados por comas; vacío = sin restricción)
PINES_ARRIBA = ''  #@param {type:"string"}
PINES_ABAJO = ''  #@param {type:"string"}
PINES_IZQUIERDA = ''  #@param {type:"string"}
PINES_DERECHA = ''  #@param {type:"string"}
ORDEN_FIJO = False  #@param {type:"boolean"}
TAMANO_ETIQUETAS = 20  #@param {type:"slider", min:5, max:50, step:5}
#@markdown ### Gráficas de ondas y vista del layout
SENALES = ''  #@param {type:"string"}
T0 = 0  #@param {type:"number"}
T1 = 3000  #@param {type:"number"}
ZOOM = ''  #@param {type:"string"}

# --- interpretación (no hace falta editar debajo de esta línea) ---
def _lista(t):
    return [x.strip() for x in str(t).replace(';', ',').split(',') if x.strip()]
_EJEMPLO = None if EJEMPLO.startswith('(') else EJEMPLO
_DENSIDAD = None if DENSIDAD.startswith('auto') else float(DENSIDAD)
_PINES = {lado: _lista(v) for lado, v in (('arriba', PINES_ARRIBA), ('abajo', PINES_ABAJO),
          ('izquierda', PINES_IZQUIERDA), ('derecha', PINES_DERECHA)) if _lista(v)}
_SENALES = _lista(SENALES) or None
_T1 = T1 if T1 and T1 > T0 else None
_ZOOM = tuple(float(x) for x in _lista(ZOOM)) or None
assert _ZOOM is None or len(_ZOOM) == 4, 'ZOOM: escribe 4 números x1, y1, x2, y2 (µm)'
if set(_PINES) & {'izquierda', 'derecha'}:
    print('AVISO: pines a izquierda/derecha compiten con las franjas de alimentación; si el ruteo no cierra, pásalos arriba/abajo')

def config(*nombres):
    \"\"\"Imprime la configuración que usa un paso.\"\"\"
    v = dict(diseño=_EJEMPLO or 'archivos subidos', densidad=_DENSIDAD or 'automática', alto_ancho=ASPECTO,
             pines=_PINES or 'libres', orden_fijo=ORDEN_FIJO, etiquetas_um=TAMANO_ETIQUETAS,
             señales=_SENALES or 'todas', ventana_ns=(T0, _T1 or 'final'), zoom=_ZOOM or 'chip completo')
    print('Configuración:', ' | '.join(f'{k} = {v[k]}' for k in nombres))

config(*'diseño densidad alto_ancho pines orden_fijo etiquetas_um señales ventana_ns zoom'.split())"""))

cells.append(md("""## 3. Tu diseño y su testbench

Escribe y revisa tu Verilog en tu editor (por ejemplo **VS Code** con una extensión de Verilog) y súbelo aquí:

- Con `EJEMPLO` = *(subir mis archivos)* en la configuración, al ejecutar la celda aparece el botón **Elegir archivos**: selecciona tu(s) `.v` de diseño
  (puedes incluir submódulos, en uno o varios archivos) y tu testbench. Opcionalmente, un `.cel2` con la posición de pines.
- El notebook detecta solo cuál es el **testbench** (archivo `*_tb.v`, o un módulo sin puertos) y cuál es el
  **módulo superior** (el que ningún otro instancia), y deja todo en `diseno/` (panel de archivos 📁).
- Si corriges algo, vuelve a ejecutar esta celda y sube la versión nueva: reemplaza a la anterior.
- Para probar con un ejemplo, elígelo en `EJEMPLO` (`counter`, `lfsr8`, `alu4`, `pwm8`) y vuelve a ejecutar la configuración.

**El testbench** debe ser el módulo superior de la simulación, guardar las ondas con `$dumpvars` (el nombre que
pongas en `$dumpfile` no importa: sirve tal cual el `dump.vcd` de EDA Playground; se aceptan `.v` y `.sv`) y
reportar con `$display`; si imprime una línea que empiece con `RESULTADO:`, el notebook la muestra como resumen.
Cambia las entradas y lee las salidas en el **flanco de bajada** del reloj (`@(negedge clk)`): si una entrada
cambia en el mismo instante que el flanco de subida, RTL y post-layout pueden resolver el empate distinto.

**Restricciones de la biblioteca `cm05`:**
- Solo **reset síncrono** (`always @(posedge clk) if (rst) ...`): el flip-flop con set/reset asíncrono (DFFSR) no está disponible porque viola la regla 8.5 de CM05.
- XOR/XNOR, sumadores completos (FAX1/HAX1) y latches tampoco están; yosys los arma con compuertas simples.
- Celdas disponibles: INV, BUF, NAND2/3, NOR2/3, AND2, OR2, AOI21/22, OAI21/22, MUX2, TBUF y DFFPOSX1."""))
cells.append(code('''config('diseño')
import re, shutil, sys
sys.path.insert(0, str(REPO_DIR / 'scripts'))
from cargar_diseno import preparar

DISENO = BASE / 'diseno'
DISENO.mkdir(exist_ok=True)
if _EJEMPLO:
    archivos = [REPO_DIR / 'examples' / _EJEMPLO / f'{_EJEMPLO}.v',
                REPO_DIR / 'examples' / _EJEMPLO / f'{_EJEMPLO}_tb.v']
else:
    SUBIDOS = BASE / 'subidos'          # copia de lo que subiste en esta ejecucion
    try:
        from google.colab import files as colab_files
        subidos = colab_files.upload()
        shutil.rmtree(SUBIDOS, ignore_errors=True); SUBIDOS.mkdir()
        archivos = []
        for nombre, datos in subidos.items():
            limpio = re.sub(r' \\(\\d+\\)(?=\\.\\w+$)', '', nombre)   # "x (1).v" -> "x.v"
            (SUBIDOS / limpio).write_bytes(datos)
            archivos.append(SUBIDOS / limpio)
            pathlib.Path(nombre).unlink(missing_ok=True)       # files.upload tambien lo deja en la carpeta actual
    except ImportError:                 # fuera de Colab: deja tus archivos en BASE/subidos
        archivos = sorted(SUBIDOS.glob('*'))

MODULO = preparar(archivos, DISENO)
RTL_V, TB_V = DISENO / f'{MODULO}.v', DISENO / f'{MODULO}_tb.v'
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
        print('Fuera de Colab; archivos en:', *map(str, rutas))'''))
cells.append(code("""# Lo que se va a usar (solo lectura, con resaltado)
from IPython.display import HTML, display
from pygments import highlight
from pygments.lexers import VerilogLexer
from pygments.formatters import HtmlFormatter
_fmt = HtmlFormatter(noclasses=True, style='friendly', linenos='inline')
for f in (RTL_V, TB_V):
    if f.exists():
        display(HTML(f'<b>{f.name}</b>' + highlight(f.read_text(), VerilogLexer(), _fmt)))"""))

cells.append(md("""## 4. Simulación RTL
Simula tu Verilog antes de mandarlo a layout. Las señales y la ventana de tiempo de la gráfica se eligen en la
configuración (`SENALES`, `T0`, `T1`).
El archivo de ondas (`<modulo>_rtl.vcd`) va en el `.zip` de resultados del final, para abrirlo en GTKWave o Surfer."""))
cells.append(code("""%%bash
cp "$DISENO/$MODULO.v" "$WORK/source/" && cp "$DISENO/${MODULO}_tb.v" "$WORK/"
bash "$REPO_DIR/scripts/cm05_sim.sh" "$MODULO" "$WORK" "$WORK/${MODULO}_tb.v" rtl 2>&1 | grep -v "typ expression"
echo "--- primeras lineas de la salida del testbench:"
head -12 "$WORK/sim_rtl/salida.txt"
"""))
cells.append(code("""import matplotlib.pyplot as plt
from vcd_plot import plot as ondas
config('señales', 'ventana_ns')

VCD_RTL = WORK / f'{MODULO}_rtl.vcd'
VCD_RTL.unlink(missing_ok=True)
if (WORK / 'sim_rtl' / 'sim.vcd').exists():
    ondas(str(WORK / 'sim_rtl' / 'sim.vcd'), _SENALES, T0, _T1)
    plt.show()
    shutil.copy(WORK / 'sim_rtl' / 'sim.vcd', VCD_RTL)
else:
    print('Sin ondas: el testbench no tiene $dumpvars (o la simulación no compiló; revisa la celda anterior).')"""))

cells.append(md("""## 5. Flujo de Verilog a GDS
Síntesis, colocación, ruteo, LVS, legalización y DRC con la densidad, proporción y pines de la configuración.
Tarda de uno a varios minutos según el tamaño del diseño."""))
cells.append(code("""import json
config('densidad', 'alto_ancho', 'pines', 'orden_fijo', 'etiquetas_um')
for k in ('CM05_DENSIDAD', 'CM05_ASPECTO', 'CM05_PINES'):
    os.environ.pop(k, None)
os.environ['CM05_TEXTO'] = str(TAMANO_ETIQUETAS)
if _DENSIDAD:
    os.environ['CM05_DENSIDAD'] = str(_DENSIDAD)
os.environ['CM05_ASPECTO'] = str(ASPECTO)
cel2 = WORK / f'{MODULO}.cel2'
cel2.unlink(missing_ok=True)
if _PINES:
    (WORK / 'pines.json').write_text(json.dumps({**_PINES, 'orden_fijo': ORDEN_FIJO}))
    os.environ['CM05_PINES'] = str(WORK / 'pines.json')
elif (DISENO / f'{MODULO}.cel2').exists():
    shutil.copy(DISENO / f'{MODULO}.cel2', cel2)
    print('Pines: se usa el .cel2 que subiste')"""))
cells.append(code("""%%bash
cp "$DISENO/$MODULO.v" "$WORK/source/" && cp "$DISENO/${MODULO}_tb.v" "$WORK/"
DECK="$PDK_DIR/tech/CIDESI_CM05/drc/drc.lydrc"
bash "$REPO_DIR/scripts/cm05_flow.sh" "$MODULO" "$WORK" "$DECK" """))

cells.append(md("""## 6. Simulación post-layout
El mismo testbench sobre el netlist que quedó en el layout ruteado (`<modulo>_postroute.v`, con los modelos
de las celdas cm05). Las trazas de texto deben ser **idénticas** a las de la simulación RTL.
La simulación es funcional (sin retardos): los tiempos del liberty son de AMI C5, no de CM05.
`<modulo>_postlayout.vcd` va en el `.zip` de resultados."""))
cells.append(code("""%%bash
cp "$DISENO/${MODULO}_tb.v" "$WORK/"
bash "$REPO_DIR/scripts/cm05_sim.sh" "$MODULO" "$WORK" "$WORK/${MODULO}_tb.v" ambos 2>&1 | grep -v "typ expression"
"""))
cells.append(code("""VCD_GATE = WORK / f'{MODULO}_postlayout.vcd'
VCD_GATE.unlink(missing_ok=True)
vr, vg = WORK / 'sim_rtl' / 'sim.vcd', WORK / 'sim_gate' / 'sim.vcd'
config('señales', 'ventana_ns')
if vr.exists() and vg.exists():
    fig, axs = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    ondas(str(vr), _SENALES, T0, _T1, ax=axs[0]); axs[0].set_title('RTL')
    ondas(str(vg), _SENALES, T0, _T1, ax=axs[1]); axs[1].set_title('Post-layout (compuertas cm05)')
    plt.tight_layout(); plt.show()
    shutil.copy(vg, VCD_GATE)
else:
    print('Sin ondas: el testbench no tiene $dumpvars (o la simulación no compiló; revisa la celda anterior).')"""))

cells.append(md("## 7. Resultados del layout"))
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

cells.append(md("""## 8. Vista de bloque
El módulo como bloque, sin detalle del layout: contorno con sus dimensiones y cada pin en su posición real
(entradas en azul hacia dentro, salidas en rojo hacia fuera, alimentación en gris). Sirve de referencia para
el floorplan; se guarda en PNG y SVG (`<modulo>_bloque.png/.svg`) y va en el `.zip` de resultados."""))
cells.append(code("""from IPython.display import Image, display
display(Image(str(WORK / f'{MODULO}_bloque.png')))"""))

cells.append(md("""## 9. Visualización del layout
El acercamiento se elige con `ZOOM` en la configuración (vacío = chip completo)."""))
cells.append(code("""import klayout.lay as klay
from IPython.display import Image, display
config('zoom')

lv = klay.LayoutView()
lv.load_layout(str(gds), True)
lv.load_layer_props(str(PDK_DIR / 'tech' / 'CIDESI_CM05' / 'CIDESI_CM05.lyp'))
lv.max_hier()
lv.set_config('background-color', '#ffffff')
lv.set_config('grid-visible', 'false')
lv.set_config('text-font', '1')       # fuente de trazos: respeta el tamaño de las etiquetas
if _ZOOM:
    lv.zoom_box(kdb.DBox(*_ZOOM))
else:
    lv.zoom_fit()
png = WORK / f'{MODULO}_cm05.png'
lv.save_image(str(png), 1400, 1050)
display(Image(str(png)))"""))

cells.append(md("""## 10. Descargar resultados
Un `.zip` con el Verilog y testbench, el GDS, la imagen del layout, la vista de bloque, los VCD de ambas simulaciones,
el netlist post-ruteo, el reporte DRC (`.lyrdb`, se abre en KLayout) y el log de qflow."""))
cells.append(code("""import zipfile
ZIP = BASE / f'{MODULO}_cm05_resultados.zip'
contenido = [RTL_V, TB_V, gds, png, WORK / f'{MODULO}_bloque.png', WORK / f'{MODULO}_bloque.svg',
             WORK / f'{MODULO}_rtl.vcd', WORK / f'{MODULO}_postlayout.vcd',
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
