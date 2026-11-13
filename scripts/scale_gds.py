"""Escala un GDS por num/den (p.ej. 25/3 para lambda 0.3 -> 2.5 um) y
reporta vértices fuera de la rejilla destino.
Uso: scale_gds.py in.gds out.gds num den rejilla_um [--strip 81/0,109/0]"""
import sys, klayout.db as db
src, dst, num, den, grid = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
ly = db.Layout(); ly.read(src)
dbu = ly.dbu
g = int(round(grid / dbu))
t = db.ICplxTrans(num/den)
off = {}
for c in ly.each_cell():
    for li in ly.layer_indexes():
        sh = c.shapes(li)
        new = []
        for s in sh.each():
            if s.is_text():
                tx = s.text.transformed(t); new.append(tx); continue
            p = s.polygon.transformed(t)
            for pt in p.each_point_hull():
                if pt.x % g or pt.y % g:
                    off[c.name] = off.get(c.name, 0) + 1
            new.append(p)
        sh.clear()
        for n in new: sh.insert(n)
    for inst in list(c.each_inst()):
        ca = inst.cell_inst
        tr = ca.trans
        inst.cell_inst = db.CellInstArray(ca.cell_index, db.Trans(tr.rot, tr.is_mirror(), tr.disp * num / den))
strip = sys.argv[sys.argv.index("--strip")+1].split(",") if "--strip" in sys.argv else []
for spec in strip:
    l, d = map(int, spec.split("/"))
    li = ly.find_layer(l, d)
    if li is not None:
        ly.delete_layer(li)
ly.write(dst)
print("celdas con vertices fuera de rejilla de", grid, "um:", off if off else "ninguna")
