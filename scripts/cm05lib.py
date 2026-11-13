"""Funciones comunes para adaptar celdas OSU a CIDESI_CM05 (lambda 2.5 um,
2 metales, sin planarizacion: Via1 a >= 2 lambda de bordes de poly/activo y de
contactos). Usado por legalize_pins.py."""
import re, itertools, klayout.db as db

LAM = 2.5
OX, PX, OY, PY = 10.0, 20.0, 12.5, 25.0     # rejilla de ruteo dentro de la celda (um)
SITE = 20.0
POWER = {"vdd", "gnd"}
CUTS = {(25, 0), (47, 0), (48, 0), (50, 0)}


class Rules:
    def __init__(self, dbu):
        u = lambda um: int(round(um / dbu))
        self.u = u
        self.S_V, self.S_V_V = u(2 * LAM), u(3 * LAM)
        self.W_M, self.S_M, self.ENC, self.VIA = u(3 * LAM), u(3 * LAM), u(LAM), u(2 * LAM)
        self.PAD = self.VIA + 2 * self.ENC


def layers(c, ly):
    R = lambda l: db.Region(c.shapes(ly.layer(l, 0))).merged()
    return dict(pa=(R(46) + R(43)).merged(), cts=(R(47) + R(48) + R(25)).merged(),
                m1=R(49), m2=R(51), vias=R(50), gate=(R(46) & R(43)))


def via_bad(v, L, rl):
    r = db.Region(v)
    pa, cts, vias = L["pa"], L["cts"], L["vias"]
    cross = not (r & pa).is_empty() and not (r - pa).is_empty()
    return (cross or not r.separation_check(pa, rl.S_V).is_empty()
            or not (r & cts).is_empty() or not r.separation_check(cts, rl.S_V).is_empty()
            or not (r & vias).is_empty()
            or (not vias.is_empty() and not r.separation_check(vias, rl.S_V_V).is_empty()))


def m_err(r, rl):
    r = r.merged()
    return r.width_check(rl.W_M).count() + r.space_check(rl.S_M).count(), r.count()


def box_at(p, size):
    h = size // 2
    return db.Box(p.x - h, p.y - h, p.x + h, p.y + h)


def bridge(a, b, w):
    h = w // 2
    r = db.Region()
    r.insert(db.Box(min(a.x, b.x) - h, a.y - h, max(a.x, b.x) + h, a.y + h))
    r.insert(db.Box(b.x - h, min(a.y, b.y) - h, b.x + h, max(a.y, b.y) + h))
    return r.merged()


# ---------------- LEF ----------------
def macro_size(mtxt):
    m = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", mtxt)
    return float(m.group(1)), float(m.group(2))


def macro_pins(mtxt, u):
    pins = {}
    for pn, body in re.findall(r"(?ms)^  PIN (\w+)\n(.*?)^  END \1\n", mtxt):
        pins[pn] = [db.Box(*[u(float(v)) for v in r]) for r in re.findall(r"RECT (\S+) (\S+) (\S+) (\S+)", body)]
    return pins


def shift_macro(mtxt, x0, d):
    """Desplaza d um todo lo que este a la derecha de x0 en pines/OBS y crece SIZE."""
    sx = lambda v: v + d if v > x0 else v
    def fr(m):
        x1, y1, x2, y2 = (float(v) for v in m.groups())
        return f"RECT {sx(x1):.3f} {y1:.3f} {sx(x2):.3f} {y2:.3f} ;"
    mtxt = re.sub(r"RECT (\S+) (\S+) (\S+) (\S+) ;", fr, mtxt)
    return re.sub(r"SIZE ([\d.]+) BY", lambda m: f"SIZE {float(m.group(1)) + d:.3f} BY", mtxt)


def rect_line(b, dbu, ind="        "):
    return f"{ind}RECT {b.left*dbu:.3f} {b.bottom*dbu:.3f} {b.right*dbu:.3f} {b.top*dbu:.3f} ;"


def rewrite_macro(mtxt, name, newpins, pins, m1, dbu):
    """Pone los pines nuevos y regenera el OBS de metal1 = M1 - (pines + espaciado)."""
    new = mtxt
    for pn, b in newpins.items():
        new = re.sub(rf"(?ms)(^  PIN {pn}\n.*?LAYER metal1 ;\n)(?:\s*RECT .*?\n)+",
                     lambda mm: mm.group(1) + rect_line(b, dbu) + "\n", new, count=1)
    allpins = db.Region()
    for pn, rects in pins.items():
        for b in ([newpins[pn]] if pn in newpins else rects):
            allpins.insert(b)
    # como en el LEF original de OSU: el OBS deja libre el espaciado minimo
    # alrededor de cada pin; si no, qrouter ve "otra red" pegada al pin y
    # desplaza la via fuera de pista
    s_m = int(round(3 * LAM / dbu))
    obs = (m1 - allpins.sized(s_m)).merged()
    lines = [rect_line(p.bbox(), dbu) for p in obs.decompose_trapezoids_to_region(db.Polygon.TD_htrapezoids).each()]
    block = "      LAYER metal1 ;\n" + "\n".join(lines) + "\n"
    if re.search(r"(?m)^\s*OBS\s*$", new):
        head, rest = re.split(r"(?m)^\s*OBS\s*\n", new, maxsplit=1)
        rest = re.sub(r"(?ms)^\s*LAYER metal1 ;\n(?:\s*RECT .*?\n)+", "", rest)
        new = head + "  OBS\n" + block + rest
    else:
        new = new.replace(f"END {name}\n", f"  OBS\n{block}  END\nEND {name}\n")
    return new


# ---------------- GDS ----------------
def stretch(c, ly, x0, d):
    """Inserta una franja de d um en x0 (um). Devuelve False si x0 cruza una compuerta."""
    X0, D = int(round(x0 / ly.dbu)), int(round(d / ly.dbu))
    L = layers(c, ly)
    if not L["gate"].interacting(db.Region(db.Box(X0, -10**9, X0 + 1, 10**9))).is_empty():
        return False
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        sh = c.shapes(li)
        new = []
        for s in sh.each():
            if s.is_text():
                t = s.text
                new.append(t.moved(D, 0) if t.x > X0 else t); continue
            p = s.polygon
            if (info.layer, info.datatype) in CUTS:
                new.append(p.moved(D, 0) if p.bbox().center().x > X0 else p)
            else:
                new.append(db.Polygon([db.Point(q.x + D if q.x > X0 else q.x, q.y) for q in p.each_point_hull()]))
        sh.clear()
        for n in new: sh.insert(n)
    return True


# ---------------- legalizacion de un pin ----------------
def legalize(c, ly, mtxt, name):
    """Intenta legalizar todos los pines de senal. Devuelve
    (macro_nueva, extensiones_M1, reporte, pines_sin_solucion)."""
    rl = Rules(ly.dbu); u = rl.u
    L = layers(c, ly)
    W, H = macro_size(mtxt)
    pins = macro_pins(mtxt, u)
    grid = [db.Point(u(OX + PX * i), u(OY + PY * j))
            for i in range(int((W - OX) // PX) + 1) for j in range(int((H - OY) // PY) + 1)]
    grid = [p for p in grid if u(5) <= p.x <= u(W - 5) and u(20) <= p.y <= u(H - 20)]
    m1 = L["m1"]
    exts, newpins, report, fails = db.Region(), {}, [], []
    for pn, rects in pins.items():
        if pn in POWER:
            continue
        ctr = rects[0].center()
        net = m1.interacting(db.Region(rects[0]))
        if not via_bad(box_at(ctr, rl.VIA), L, rl) and (db.Region(box_at(ctr, rl.PAD)) - net).is_empty():
            continue
        base = m_err(m1, rl)
        best = None
        for p in sorted(grid, key=lambda q: (abs(q.x - ctr.x) + abs(q.y - ctr.y), abs(q.x - ctr.x))):
            if via_bad(box_at(p, rl.VIA), L, rl):
                continue
            m2pad = db.Region(box_at(p, rl.PAD))
            if not L["m2"].is_empty() and (not (m2pad & L["m2"]).is_empty()
                                           or not m2pad.separation_check(L["m2"], rl.S_M).is_empty()):
                continue
            pad = db.Region(box_at(p, rl.PAD))
            if (pad - net).is_empty():
                best = (p, db.Region()); break
            for ext in (bridge(ctr, p, rl.W_M) + pad, bridge(p, ctr, rl.W_M) + pad):
                bb = ext.bbox()
                if bb.left < u(5) or bb.right > u(W - 5):
                    continue
                e = m_err(m1 + ext, rl)
                if e[0] <= base[0] and e[1] == base[1]:
                    best = (p, ext); break
            if best:
                break
        if not best:
            fails.append(pn); continue
        p, ext = best
        if not ext.is_empty():
            m1 = (m1 + ext).merged(); exts += ext
        newpins[pn] = box_at(p, rl.PAD)
        report.append(f"{name}.{pn}: ({ctr.x*ly.dbu:.1f},{ctr.y*ly.dbu:.1f}) -> ({p.x*ly.dbu:.1f},{p.y*ly.dbu:.1f})"
                      + (" +M1" if not ext.is_empty() else ""))
    new = rewrite_macro(mtxt, name, newpins, pins, m1, ly.dbu) if newpins else mtxt
    return new, exts, report, fails
