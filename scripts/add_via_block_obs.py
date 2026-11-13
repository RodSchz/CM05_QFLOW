#!/usr/bin/env python3
"""Impide que qrouter coloque vias de ruteo (a mitad de ruta) sobre las celdas
en puntos donde CM05 no permite Via1 (reglas 8.4/8.5).

qrouter no respeta obstrucciones en la capa de corte, pero si en metal1: una via
necesita su pad de M1 libre. Para cada punto de la rejilla de ruteo dentro de la
celda donde una via seria ilegal, se agrega un cuadro de OBS de metal1 de 1/2
lambda de lado, centrado en el punto. El cuadro no toca ningun metal existente,
asi que en la vista abstracta de magic no une redes (a diferencia de una OBS
grande en la capa via, que si cortocircuita pines).

Se aplica una sola vez sobre un LEF recien construido (build_cm05_tech.sh).
Uso: add_via_block_obs.py lib.gds lib.lef [CELDA,...|--todas]
"""
import os, re, sys, klayout.db as db
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm05lib as K

gds, lef = sys.argv[1], sys.argv[2]
ly = db.Layout(); ly.read(gds)
rl = K.Rules(ly.dbu); u = rl.u
txt = open(lef).read()
macros = re.findall(r"(?ms)^MACRO (\w+)\n.*?^END \1\n", txt)
want = set(macros) if len(sys.argv) < 4 or sys.argv[3] == "--todas" else set(sys.argv[3].split(","))
HALF = u(K.LAM / 4)          # cuadro de 1.25 um

total = 0
for name in macros:
    if name not in want or ly.cell(name) is None or name.startswith("FILL"):
        continue
    mtxt = re.search(rf"(?ms)^MACRO {name}\n.*?^END {name}\n", txt).group(0)
    L = K.layers(ly.cell(name), ly)
    W, H = K.macro_size(mtxt)
    pins = K.macro_pins(mtxt, u)
    pinreg = db.Region([b for pn, bs in pins.items() for b in bs])
    rects = []
    for i in range(int((W - K.OX) // K.PX) + 1):
        for j in range(int((H - K.OY) // K.PY) + 1):
            p = db.Point(u(K.OX + K.PX * i), u(K.OY + K.PY * j))
            if not (0 < p.x < u(W) and 0 < p.y < u(H)):
                continue
            if not K.via_bad(K.box_at(p, rl.VIA), L, rl):
                continue
            sq = db.Box(p.x - HALF, p.y - HALF, p.x + HALF, p.y + HALF)
            if not (db.Region(sq) & (L["m1"] + pinreg)).is_empty():
                continue        # ya hay metal: el punto esta bloqueado o es pin
            if not db.Region(sq).separation_check(L["m1"] + pinreg, 1).is_empty():
                continue
            rects.append(K.rect_line(sq, ly.dbu))
    if not rects:
        continue
    block = "      LAYER metal1 ;\n" + "\n".join(rects) + "\n"
    if re.search(r"(?m)^\s*OBS\s*$", mtxt):
        new = re.sub(r"(?m)^\s*OBS\s*\n", lambda m: m.group(0) + block, mtxt, count=1)
    else:
        new = mtxt.replace(f"END {name}\n", f"  OBS\n{block}  END\nEND {name}\n")
    txt = txt.replace(mtxt, new)
    total += len(rects)
open(lef, "w").write(txt)
print(f"cuadros de bloqueo de via agregados: {total}")
