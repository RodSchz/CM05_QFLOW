#!/usr/bin/env python3
"""Arma filas de prueba con todas las celdas de la biblioteca pegadas (normal,
espejo en x, y alternando) para verificar con el DRC que el abutamiento entre
cualquier par vecino es legal. Anchos tomados del LEF.
Uso: abut_test.py lib.gds lib.lef CELDA,CELDA,... out.gds"""
import re, sys, klayout.db as db
gds, lef, cells, out = sys.argv[1], sys.argv[2], sys.argv[3].split(","), sys.argv[4]
W = {m: float(w) for m, w in re.findall(r"(?ms)^MACRO (\w+)\n.*?SIZE ([\d.]+) BY", open(lef).read())}
ly = db.Layout(); ly.read(gds)
top = ly.create_cell("ABUT")
H = 250.0
def place(order, y, mirror_x_alt, mirror_x_all, flip_y):
    x = 0.0
    for k, c in enumerate(order):
        w = W[c]
        mx = mirror_x_all or (mirror_x_alt and k % 2)
        if flip_y:      # fila espejada en y (FS de qflow): comparte riel con la de abajo
            t = db.DCplxTrans(1, 180, False, x + w, y + 2 * H) if mx else db.DCplxTrans(1, 0, True, x, y + 2 * H)
        else:
            t = db.DCplxTrans(1, 180, True, x + w, y) if mx else db.DCplxTrans(1, 0, False, x, y)
        top.insert(db.DCellInstArray(ly.cell(c).cell_index(), t))
        x += w
y = 0.0
for order in (cells, cells[::-1]):
    for alt, allm in ((False, False), (False, True), (True, False)):
        place(order, y, alt, allm, False)      # fila N
        place(order[1:] + order[:1], y, not alt, allm, True)   # fila FS encima, desfasada
        y += 3 * H
ly.write(out)
print("filas de prueba:", out)
