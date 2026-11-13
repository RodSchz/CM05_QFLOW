#!/usr/bin/env python3
"""Integra una celda corregida a la biblioteca cm05 (GDS + LEF).

- GDS: reemplaza la celda en el GDS de la biblioteca por la del archivo corregido.
- LEF: SIZE y pines se recalculan con el mismo estiramiento (X0, D) que se uso en
  stretch_cell.py (D = 0 si no hubo estiramiento); el bloque OBS se regenera
  desde la geometria nueva: metal1 (menos los pines), metal2 y via.

Uso: apply_cell_fix.py lib.gds lib.lef celda_fix.gds CELDA X0[,X0...] D_um   (X0 vacio "" = sin ensanche)
"""
import re, sys, klayout.db as db

lib_gds, lib_lef, fix_gds, name = sys.argv[1:5]
cuts = [float(v) for v in sys.argv[5].split(",") if v]   # cortes en orden de aplicacion
d = float(sys.argv[6])

# ---------- GDS ----------
lib = db.Layout(); lib.read(lib_gds)
fix = db.Layout(); fix.read(fix_gds)
old = lib.cell(name)
old.clear()
old.copy_tree(fix.cell(name))
lib.write(lib_gds)
fc = fix.cell(name)
dbu = fix.dbu

# ---------- LEF ----------
txt = open(lib_lef).read()
m = re.search(rf"^MACRO {name}\n.*?^END {name}\n", txt, re.S | re.M)
macro = m.group(0)
def sx(v):
    for x0 in cuts:          # cada corte esta en coordenadas tras los anteriores
        if v > x0: v += d
    return v
def fix_rect(line):
    nums = [float(v) for v in re.findall(r"-?\d+\.\d+", line)]
    x1, y1, x2, y2 = nums
    lead = line[: len(line) - len(line.lstrip())]
    return f"{lead}RECT {sx(x1):.3f} {y1:.3f} {sx(x2):.3f} {y2:.3f} ;"

head, obs = macro.split("  OBS", 1)
head = re.sub(r"(?m)^\s*RECT .*$", lambda mm: fix_rect(mm.group(0)), head)
head = re.sub(r"SIZE ([\d.]+) BY", lambda mm: f"SIZE {float(mm.group(1)) + d*len(cuts):.3f} BY", head)

pins = db.Region()
for r in re.findall(r"RECT (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)", head):
    x1, y1, x2, y2 = (int(round(float(v) / dbu)) for v in r)
    pins.insert(db.Box(x1, y1, x2, y2))

def rects(region):
    out = []
    for p in region.merged().decompose_trapezoids_to_region(db.Polygon.TD_htrapezoids).each():
        b = p.bbox()
        out.append(f"        RECT {b.left*dbu:.3f} {b.bottom*dbu:.3f} {b.right*dbu:.3f} {b.top*dbu:.3f} ;")
    return out

R = lambda l: db.Region(fc.shapes(fix.layer(l, 0)))
blocks = [("metal2", R(51)), ("metal1", R(49) - pins.sized(int(round(7.5 / dbu)))), ("via", R(50))]  # hueco de espaciado alrededor de pines, como OSU
obs_txt = "  OBS\n" + "".join(f"      LAYER {ln} ;\n" + "\n".join(rects(r)) + "\n" for ln, r in blocks if not r.is_empty()) + "  END\n"
new_macro = head + obs_txt + f"END {name}\n"
txt = txt.replace(macro, new_macro)
open(lib_lef, "w").write(txt)
print(f"{name}: GDS reemplazado; LEF ensanchado {d*len(cuts)} um (cortes {cuts}); OBS regenerado")
