#!/usr/bin/env python3
"""Corrige las vias internas de una celda para la regla 8.5 de CM05,
ensanchandola de forma automatica cuando no basta con reubicarlas.

Ciclo: reubica vias (fix_via_rule85.py, con margen de 5 um al borde); si queda
alguna sin solucion, prueba cortes verticales cerca de ella (stretch de un sitio,
sin cruzar compuertas), reubica de nuevo y se queda con el primer corte que deja
cero vias sin solucion. Repite hasta resolver o agotar --max-ensanches.
Imprime los cortes usados en una ultima linea "CORTES: x0 x0 ..." para que el
LEF se ajuste igual (apply_cell_fix.py / shift).

Uso: fix_cell_vias.py in.gds CELDA out.gds ANCHO_um [--max-ensanches N]
"""
import os, re, subprocess, sys, tempfile, shutil, klayout.db as db
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm05lib as K

src, cell, dst, W = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
MAXS = int(sys.argv[sys.argv.index("--max-ensanches") + 1]) if "--max-ensanches" in sys.argv else 3
HERE = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp()

def fix(inp, out, width):
    r = subprocess.run([sys.executable, "-I", f"{HERE}/fix_via_rule85.py", inp, cell, out, "2.5", "40", str(width)],
                       capture_output=True, text=True)
    fails = [tuple(float(v) for v in m) for m in re.findall(r"via ([\d.-]+),([\d.-]+): SIN", r.stdout)]
    return fails, r.stdout

def stretched(inp, out, x0):
    ly = db.Layout(); ly.read(inp)
    if not K.stretch(ly.cell(cell), ly, x0, K.SITE):
        return False
    ly.write(out); return True

cur = f"{tmp}/c0.gds"
fails, log = fix(src, cur, W)
print(log.strip())
cuts = []
while fails and len(cuts) < MAXS:
    width = W + K.SITE * len(cuts)
    fx = [f[0] for f in fails]
    cands = sorted({round((f + k * 1.25) / 1.25) * 1.25 for f in fx for k in range(-30, 31)
                    if 2.5 < f + k * 1.25 < width - 2.5}, key=lambda x: min(abs(x - f) for f in fx))
    best = None
    for x0 in cands[:50]:
        s = f"{tmp}/s.gds"; o = f"{tmp}/o_{x0}.gds"
        if not stretched(cur, s, x0):
            continue
        f2, log2 = fix(s, o, width + K.SITE)
        if best is None or len(f2) < len(best[1]):
            best = (x0, f2, o, log2)
            if not f2:
                break
    if best is None or len(best[1]) >= len(fails):
        break
    cuts.append(best[0]); fails, cur = best[1], best[2]
    print(f"ensanche en x={best[0]} um\n{best[3].strip()}")
shutil.copy(cur, dst)
shutil.rmtree(tmp)
print(f"sin solucion: {len(fails)}")
print("CORTES: " + " ".join(str(c) for c in cuts))
sys.exit(1 if fails else 0)
