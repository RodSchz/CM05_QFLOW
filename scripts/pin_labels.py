#!/usr/bin/env python3
"""Ajusta las etiquetas de los pines de E/S del GDS final.

magic escribe las etiquetas de los puertos en las capas de dibujo (49/0, 51/0)
con 0.3 um de alto, casi invisibles en un chip de milímetros. Este paso:
  - las mueve a las capas de texto del PDK CIDESI_CM05 (49/1 Metal1.text,
    51/1 Metal2.text), que son las que lee su LVS (labels(49,1), labels(51,1));
  - les da un tamaño legible (por omisión 20 um).
Solo toca las etiquetas de la celda superior; las celdas no cambian.

Uso: pin_labels.py <diseno.gds> <TOP> [alto_um=20]
"""
import sys, klayout.db as db

gds, top_name = sys.argv[1], sys.argv[2]
alto = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
ly = db.Layout(); ly.read(gds)
top = ly.cell(top_name)
size = int(round(alto / ly.dbu))
n = 0
for dib, txt in (((49, 0), (49, 1)), ((51, 0), (51, 1))):
    li = ly.find_layer(*dib)
    if li is None:
        continue
    lt = ly.layer(*txt)
    for s in list(top.shapes(li).each()):
        if not s.is_text():
            continue
        t = s.text.dup()
        t.trans = db.Trans(db.Vector(t.x, t.y))   # horizontal y sin espejo (magic las gira)
        t.size = size
        t.halign = db.HAlign.HAlignCenter
        t.valign = db.VAlign.VAlignCenter
        top.shapes(lt).insert(t)
        top.shapes(li).erase(s)
        n += 1
ly.write(gds)
print(f"   etiquetas de pines: {n} en capas de texto 49/1 y 51/1, alto {alto:g} um")
