#!/usr/bin/env python3
"""Ensancha una celda insertando una franja vertical de ancho D en x = X0.

Todo vertice con x > X0 se desplaza +D, de modo que los poligonos que cruzan X0
(difusiones, selects, pozos, rieles, metales horizontales) se alargan.
Los cortes (contactos 25/47/48 y vias 50) no se estiran: se desplazan enteros
segun su centro. Aborta si X0 cruza una compuerta (poly sobre activo), porque
estirarla cambiaria W o L del transistor.

Uso: stretch_cell.py in.gds CELDA out.gds X0_um D_um
"""
import sys, klayout.db as db

src, cell, dst, x0, d = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
ly = db.Layout(); ly.read(src)
c = ly.cell(cell)
X0, D = int(round(x0 / ly.dbu)), int(round(d / ly.dbu))
CUTS = {(25, 0), (47, 0), (48, 0), (50, 0)}

gate = (db.Region(c.shapes(ly.layer(46, 0))) & db.Region(c.shapes(ly.layer(43, 0))))
if not gate.interacting(db.Region(db.Box(X0, -10**9, X0 + 1, 10**9))).is_empty():
    sys.exit(f"X0={x0} cruza una compuerta: elegir otro corte")

def stretch_poly(p):
    pts = [db.Point(q.x + D if q.x > X0 else q.x, q.y) for q in p.each_point_hull()]
    return db.Polygon(pts)

for li in ly.layer_indexes():
    info = ly.get_info(li)
    sh = c.shapes(li)
    new = []
    for s in sh.each():
        if s.is_text():
            t = s.text
            if t.x > X0: t = t.moved(D, 0)
            new.append(t); continue
        p = s.polygon
        if (info.layer, info.datatype) in CUTS:
            new.append(p.moved(D, 0) if p.bbox().center().x > X0 else p)
        else:
            new.append(stretch_poly(p))
    sh.clear()
    for n in new: sh.insert(n)
ly.write(dst)
print(f"{cell}: franja de {d} um insertada en x={x0} um; nuevo bbox {c.dbbox()}")
