#!/usr/bin/env python3
"""Legalizador post-ruteo para CIDESI_CM05 (2 metales, sin planarizacion).

qrouter no sabe que CM05 prohibe Via1 cerca de bordes de poly/activo
(regla 8.5) ni de contactos (8.4), y deja muescas de mismo net en metal que el
deck de KLayout marca como espaciado (7.2/9.2). Este script, sobre el GDS final:

 1. Para cada via del nivel superior (vias de ruteo) que viole 8.4/8.5/8.2,
    busca la posicion mas cercana en la rejilla de 1/2 lambda donde la via
    cumpla, y la une a su pad original con parches de M1 y M2 en L. Una
    posicion solo se acepta si no crea errores de ancho/espaciado nuevos ni
    fusiona poligonos de metal distintos (sin cortos). Todo se evalua sobre la
    geometria aplanada (celdas + ruteo) en una ventana local.
 2. Rellena muescas (notch) de M1 y M2 menores al espaciado minimo, que por
    definicion son del mismo poligono (mismo net).

Los parches se agregan a la celda superior; las celdas no se tocan.
Uso: fix_route_vias.py in.gds TOP out.gds [lambda_um=2.5] [radio_um=40]
"""
import sys, itertools, klayout.db as db

src, top_name, dst = sys.argv[1:4]
LAM = float(sys.argv[4]) if len(sys.argv) > 4 else 2.5
RADIO = float(sys.argv[5]) if len(sys.argv) > 5 else 40.0
ly = db.Layout(); ly.read(src)
top = ly.cell(top_name)
u = lambda um: int(round(um / ly.dbu))
li = lambda l: ly.layer(l, 0)
flat = lambda l: db.Region(top.begin_shapes_rec(li(l))).merged()

S_V_PA, S_V_CT, S_V_V = u(2 * LAM), u(2 * LAM), u(3 * LAM)
W_M, S_M, ENC, GRID, VIA = u(3 * LAM), u(3 * LAM), u(LAM), u(LAM / 2), u(2 * LAM)
WIN = u(RADIO) + u(20 * LAM)

PA = (flat(46) + flat(43)).merged()
CTS = (flat(47) + flat(48) + flat(25)).merged()
M1, M2, V1 = flat(49), flat(51), flat(50)
top_vias = [s for s in top.shapes(li(50)).each() if not s.is_text()]

def via_bad(v, vias, pa, cts):
    """8.5: la via debe quedar a >= 2 lambda de cualquier BORDE de poly/activo
    (fuera de ellos; el deck no marca una via completamente dentro de poly/activo,
    pero si una que cruce su borde). 8.4: fuera de contactos y a
    >= 2 lambda. 8.2: espaciado via-via."""
    r = db.Region(v)
    # cruza un borde (parte dentro y parte fuera); dentro por completo lo acepta el deck
    near_edge = not (r & pa).is_empty() and not (r - pa).is_empty()
    return (near_edge or not r.separation_check(pa, S_V_PA).is_empty()
            or not (r & cts).is_empty() or not r.separation_check(cts, S_V_CT).is_empty()
            or not r.separation_check(vias, S_V_V).is_empty())

def metal_state(reg, win):
    w = (reg & db.Region(win)).merged()
    return w.width_check(W_M).count() + w.space_check(S_M).count(), w.count()

def bridge(a, b, w):
    h = w // 2
    r = db.Region()
    r.insert(db.Box(min(a.x, b.x) - h, a.y - h, max(a.x, b.x) + h, a.y + h))
    r.insert(db.Box(b.x - h, min(a.y, b.y) - h, b.x + h, max(a.y, b.y) + h))
    return r.merged()

patch_m1, patch_m2 = db.Region(), db.Region()
moved, failed = 0, []
for s in top_vias:
    v = s.box
    ctr = v.center()
    win = db.Box(ctr.x - WIN, ctr.y - WIN, ctr.x + WIN, ctr.y + WIN)
    big = db.Region(win.enlarged(u(10 * LAM), u(10 * LAM)))
    pa, cts = PA & big, CTS & big
    m1w, m2w = (M1 & big).merged(), (M2 & big).merged()
    others = (V1 & big) - db.Region(v)
    if not via_bad(v, others, pa, cts):
        continue
    b1, b2 = metal_state(m1w, win), metal_state(m2w, win)
    rng = range(-u(RADIO), u(RADIO) + 1, GRID)
    found = None
    for dx, dy in sorted(itertools.product(rng, rng), key=lambda d: (abs(d[0]) + abs(d[1]), abs(d[0]))):
        if (dx, dy) == (0, 0):
            continue
        nc = db.Point(ctr.x + dx, ctr.y + dy)
        nv = db.Box(nc.x - VIA // 2, nc.y - VIA // 2, nc.x + VIA // 2, nc.y + VIA // 2)
        if via_bad(nv, others, pa, cts):
            continue
        pad = db.Region(nv.enlarged(ENC, ENC))
        for a, b in ((ctr, nc), (nc, ctr)):
            p = bridge(a, b, VIA + 2 * ENC) + pad
            n1, n2 = (m1w + p).merged(), (m2w + p).merged()
            e1, e2 = metal_state(n1, win), metal_state(n2, win)
            if e1[0] <= b1[0] and e2[0] <= b2[0] and e1[1] == b1[1] and e2[1] == b2[1]:
                found = (nv, p, n1, n2, dx, dy); break
        if found:
            break
    if not found:
        failed.append(ctr); continue
    nv, p, _, _, dx, dy = found
    top.shapes(li(50)).erase(s)
    top.shapes(li(50)).insert(nv)
    M1 = (M1 + p).merged(); M2 = (M2 + p).merged()
    V1 = (V1 - db.Region(v)) + db.Region(nv)
    patch_m1 += p; patch_m2 += p
    moved += 1

# muescas del mismo poligono menores al espaciado minimo
notch = {}
for name, l, reg in (("M1", 49, M1), ("M2", 51, M2)):
    fill = db.Region()
    for ep in reg.notch_check(S_M).each():
        fill.insert(ep.polygon(0))
    notch[name] = fill.count()
    top.shapes(li(l)).insert(fill.merged())
top.shapes(li(49)).insert(patch_m1.merged())
top.shapes(li(51)).insert(patch_m2.merged())
ly.write(dst)
print(f"vias de ruteo reubicadas: {moved}; sin solucion: {len(failed)} {[(p.x*ly.dbu, p.y*ly.dbu) for p in failed]}")
print(f"muescas rellenadas: M1 {notch['M1']}, M2 {notch['M2']}")
