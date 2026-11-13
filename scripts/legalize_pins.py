#!/usr/bin/env python3
"""Legaliza el acceso a pines de la biblioteca cm05 (2 metales, sin
planarizacion; reglas 8.4/8.5 de CIDESI_CM05).

qrouter baja a cada pin con una via M2->M1 centrada en el cuadro del pin. Para
cada pin de senal cuyo punto no admite una via legal:
  1. Busca el punto de la rejilla de ruteo mas cercano donde la via es legal y
     el pad M1 cae sobre la misma red o se le une con una extension de M1 en L
     sin violar ancho/espaciado ni tocar otra red.
  2. Si ningun punto sirve, ensancha la celda un sitio (20 um) con un corte
     vertical cercano que no cruce compuertas (solo se alargan formas
     horizontales) y vuelve a intentar. Elige el corte que deja menos pines sin
     solucion; repite hasta resolverlos o agotar intentos.
El pin del LEF pasa al punto legal; el OBS de metal1 se regenera (M1 - pines).
Las extensiones de M1 y los ensanches se escriben al GDS de la celda.

Uso: legalize_pins.py lib.gds lib.lef CELDA[,CELDA...] | --todas  [--max-ensanches N]
"""
import os, re, sys, klayout.db as db
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cm05lib as K

gds, lef = sys.argv[1], sys.argv[2]
MAXS = int(sys.argv[sys.argv.index("--max-ensanches") + 1]) if "--max-ensanches" in sys.argv else 3
ly = db.Layout(); ly.read(gds)
txt = open(lef).read()
macros = re.findall(r"(?ms)^MACRO (\w+)\n.*?^END \1\n", txt)
want = set(macros) if "--todas" in sys.argv else set(sys.argv[3].split(","))
um = lambda v: int(round(v / ly.dbu))


def try_cell(src_cell, mtxt, name, cuts):
    """Copia la celda, aplica los cortes (lista de x0, en orden) y legaliza."""
    tmp = db.Layout(); tmp.dbu = ly.dbu
    c = tmp.create_cell(name); c.copy_tree(src_cell)
    m = mtxt
    for x0 in cuts:
        if not K.stretch(c, tmp, x0, K.SITE):
            return None
        m = K.shift_macro(m, x0, K.SITE)
    new, exts, rep, fails = K.legalize(c, tmp, m, name)
    return dict(c=c, tmp=tmp, new=new, exts=exts, rep=rep, fails=fails, macro=m)


summary = []
for name in macros:
    if name not in want or ly.cell(name) is None:
        continue
    mtxt = re.search(rf"(?ms)^MACRO {name}\n.*?^END {name}\n", txt).group(0)
    res = try_cell(ly.cell(name), mtxt, name, [])
    cuts = []
    while res["fails"] and len(cuts) < MAXS:
        W, _ = K.macro_size(res["macro"])
        pins = K.macro_pins(res["macro"], um)
        fx = [pins[p][0].center().x * ly.dbu for p in res["fails"]]
        cands = sorted({round(x / 1.25) * 1.25 for f in fx for x in
                        (f + k * 1.25 for k in range(-40, 41)) if 2.5 < x < W - 2.5},
                       key=lambda x: min(abs(x - f) for f in fx))
        best = None
        for x0 in cands[:60]:
            r = try_cell(ly.cell(name), mtxt, name, cuts + [x0])
            if r is None:
                continue
            if best is None or len(r["fails"]) < len(best[1]["fails"]):
                best = (x0, r)
                if not r["fails"]:
                    break
        if best is None or len(best[1]["fails"]) >= len(res["fails"]):
            break
        cuts.append(best[0]); res = best[1]
    if res["new"] == mtxt and not cuts:
        continue
    tgt = ly.cell(name)
    tgt.clear(); tgt.copy_tree(res["c"])
    if not res["exts"].is_empty():
        tgt.shapes(ly.layer(49, 0)).insert(res["exts"])
    txt = txt.replace(mtxt, res["new"])
    summary.append(f"{name}: ensanches en x={cuts} (+{K.SITE*len(cuts):.0f} um); "
                   f"{len(res['rep'])} pines movidos; sin solucion: {res['fails'] or 'ninguno'}")
    summary += ["    " + r for r in res["rep"]]

ly.write(gds)
open(lef, "w").write(txt)
print("\n".join(summary) if summary else "todos los pines ya eran legales")
