#!/usr/bin/env python3
"""Reubica vias (50/0) de una celda para cumplir la regla 8.5 de CIDESI_CM05
(Via1 a >= 2 lambda de bordes de poly/activo) sin romper el resto de reglas.

Para cada via que viola, prueba posiciones cercanas en la rejilla de 1/2 lambda,
mueve el corte y une el pad nuevo con el viejo mediante parches de M1 y M2
(forma de L si hace falta). Una posicion se acepta solo si:
  - la via cumple 8.5 (separacion a poly/activo), 8.4 (a contactos), 8.2 (via-via)
  - M1 y M2 no generan nuevas violaciones de ancho/espaciado (7.1/7.2, 9.1/9.2)
  - no se fusionan poligonos de metal que antes estaban separados (sin cortos)
Se elige la reubicacion de menor desplazamiento.

Uso: fix_via_rule85.py in.gds CELDA out.gds [lambda_um=2.5] [radio_um=40] [ancho_celda_um]
"""
import sys, itertools, klayout.db as db

src, cellname, dst = sys.argv[1:4]
LAM = float(sys.argv[4]) if len(sys.argv) > 4 else 2.5
RADIO = float(sys.argv[5]) if len(sys.argv) > 5 else 40.0   # um
ANCHO = float(sys.argv[6]) if len(sys.argv) > 6 else None   # ancho de la celda (um)
ly = db.Layout(); ly.read(src)
c = ly.cell(cellname)
u = lambda um: int(round(um / ly.dbu))
L = {n: ly.layer(*lp) for n, lp in dict(PL=(46, 0), AA=(43, 0), CTP=(47, 0), CTA=(48, 0),
                                       CT=(25, 0), M1=(49, 0), V1=(50, 0), M2=(51, 0)).items()}
reg = lambda n: db.Region(c.shapes(L[n])).merged()

S_V_PA = u(2 * LAM)        # 8.5
S_V_CT = u(2 * LAM)        # 8.4
S_V_V = u(3 * LAM)         # 8.2
W_M, S_M = u(3 * LAM), u(3 * LAM)   # 7.1/7.2 y 9.1/9.2 (SUBM)
ENC = u(1 * LAM)           # 7.3/8.3/9.3
GRID = u(LAM / 2)
VIA = u(2 * LAM)
PA = (reg("PL") + reg("AA")).merged()
CTS = (reg("CTP") + reg("CTA") + reg("CT")).merged()

def via_bad(v, others):
    vr = db.Region(v)
    return (not vr.separation_check(PA, S_V_PA).is_empty() or not (vr & PA).is_empty()
            or not vr.separation_check(CTS, S_V_CT).is_empty() or not (vr & CTS).is_empty()
            or not vr.separation_check(others, S_V_V).is_empty())

def metal_errs(r):
    r = r.merged()
    return r.width_check(W_M).count() + r.space_check(S_M).count(), r.count()

def bridge(a, b, w):
    """Parche en L de ancho w entre los centros a y b (primero x, luego y)."""
    h = w // 2
    r = db.Region()
    r.insert(db.Box(min(a.x, b.x) - h, a.y - h, max(a.x, b.x) + h, a.y + h))
    r.insert(db.Box(b.x - h, min(a.y, b.y) - h, b.x + h, max(a.y, b.y) + h))
    return r

vias = [s.box for s in c.shapes(L["V1"]).each()]
m1, m2 = reg("M1"), reg("M2")
base1, base2 = metal_errs(m1), metal_errs(m2)
moved = []
for i, v in enumerate(vias):
    others = db.Region([b for j, b in enumerate(vias) if j != i])
    if not via_bad(v, others):
        continue
    ctr = v.center()
    best = None
    rng = range(-u(RADIO), u(RADIO) + 1, GRID)
    for dx, dy in sorted(itertools.product(rng, rng), key=lambda d: abs(d[0]) + abs(d[1])):
        if best and abs(dx) + abs(dy) > best[0]:
            break
        if dx == dy == 0:
            continue
        for order in (0, 1):   # L: x-luego-y o y-luego-x
            nc = db.Point(ctr.x + dx, ctr.y + dy)
            nv = db.Box(nc.x - VIA // 2, nc.y - VIA // 2, nc.x + VIA // 2, nc.y + VIA // 2)
            if via_bad(nv, others):
                break
            pad = VIA + 2 * ENC
            a, b = (ctr, nc) if order == 0 else (nc, ctr)
            patch = bridge(a, b, max(pad, W_M)) + db.Region(nv.enlarged(ENC, ENC))
            if ANCHO is not None and (patch.bbox().left < u(5) or patch.bbox().right > u(ANCHO - 5)):
                continue   # >= 5 um del borde: espaciado con la celda vecina abutada
            n1 = (m1 + patch).merged(); n2 = (m2 + patch).merged()
            e1, e2 = metal_errs(n1), metal_errs(n2)
            # sin errores nuevos y mismo numero de poligonos (sin cortos)
            if e1[0] <= base1[0] and e2[0] <= base2[0] and e1[1] == base1[1] and e2[1] == base2[1]:
                best = (abs(dx) + abs(dy), nv, n1, n2, (dx, dy))
                break
    if not best:
        print(f"via {ctr*ly.dbu}: SIN solucion local"); continue
    _, nv, m1, m2, d = best
    vias[i] = nv
    moved.append((ctr * ly.dbu, d[0] * ly.dbu, d[1] * ly.dbu))
    base1, base2 = metal_errs(m1), metal_errs(m2)

for n, r in (("M1", m1), ("M2", m2)):
    texts = [t.text for t in c.shapes(L[n]).each() if t.is_text()]   # etiquetas de pines
    c.shapes(L[n]).clear(); c.shapes(L[n]).insert(r)
    for t in texts: c.shapes(L[n]).insert(t)
c.shapes(L["V1"]).clear()
for b in vias: c.shapes(L["V1"]).insert(b)
ly.write(dst)
for p, dx, dy in moved:
    print(f"via en ({p.x:.2f},{p.y:.2f}) movida dx={dx:+.2f} dy={dy:+.2f} um")
print(f"{len(moved)} vias reubicadas")
