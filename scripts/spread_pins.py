#!/usr/bin/env python3
"""Reparte los pines de E/S a lo largo de cada lado del chip en el DEF colocado,
sobre pistas de ruteo, conservando el lado y el orden que eligió graywolf.

Con restricciones de lado (.cel2), graywolf tiende a amontonar los pines (a
5 um entre sí cuando las pistas están cada 20-25 um), y con solo 2 metales el
ruteo ya no cierra. Este paso corre entre `qflow place` y `qflow route`.

Pines izquierda/derecha: en metal1, sobre pistas Y; arriba/abajo: metal2, pistas X.
Uso: spread_pins.py <diseno.def> [<diseno.def> ...]
"""
import re, sys


def spread(path):
    t = open(path).read()
    die = re.search(r"DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", t)
    x0, y0, x1, y1 = map(int, die.groups())
    tracks = {}
    for m in re.finditer(r"TRACKS ([XY]) (-?\d+) DO (\d+) STEP (\d+) LAYER (\w+)", t):
        ax, start, n, step, _ = m.groups()
        tracks[ax] = [int(start) + int(step) * i for i in range(int(n))]
    pins_blk = re.search(r"(?ms)^PINS \d+ ;\n(.*?)^END PINS", t)
    body = pins_blk.group(1)
    pins = re.findall(r"(?ms)^- (\S+) \+ NET \S+\n.*?\+ PLACED \( (-?\d+) (-?\d+) \) \w+ ;", body)
    lados = {"L": [], "R": [], "B": [], "T": []}
    for name, px, py in pins:
        if name in ("vdd", "gnd"):
            continue
        px, py = int(px), int(py)
        d = {"L": px - x0, "R": x1 - px, "B": py - y0, "T": y1 - py}
        lado = min(d, key=d.get)
        lados[lado].append((py if lado in "LR" else px, name))
    nuevo = {}
    for lado, lst in lados.items():
        if not lst:
            continue
        lst.sort()
        pistas = tracks["Y" if lado in "LR" else "X"]
        lo, hi = (y0, y1) if lado in "LR" else (x0, x1)
        paso = pistas[1] - pistas[0]
        usable = [p for p in pistas if lo + 2 * paso <= p <= hi - 2 * paso]
        n = len(lst)
        if n > len(usable):
            print(f"  {path}: lado {lado} con {n} pines y {len(usable)} pistas; se deja como esta")
            continue
        elegidas = []
        for k in range(n):
            ideal = lo + (hi - lo) * (k + 0.5) / n
            libres = [p for p in usable if p not in elegidas]
            elegidas.append(min(libres, key=lambda p: abs(p - ideal)))
        elegidas.sort()
        for (_, name), pos in zip(lst, elegidas):
            nuevo[name] = (lado, pos)

    def rep(m):
        name = m.group(1)
        if name not in nuevo:
            return m.group(0)
        lado, pos = nuevo[name]
        px, py = int(m.group(2)), int(m.group(3))
        if lado in "LR":
            py = pos
        else:
            px = pos
        return m.group(0)[: m.start(2) - m.start(0)] + f"{px} {py}" + m.group(0)[m.end(3) - m.start(0):]

    body2 = re.sub(r"(?ms)^- (\S+) \+ NET \S+\n.*?\+ PLACED \( (-?\d+) (-?\d+) \) \w+ ;", rep, body)
    open(path, "w").write(t[: pins_blk.start(1)] + body2 + t[pins_blk.end(1):])
    return sum(len(v) for v in lados.values())


for p in sys.argv[1:]:
    n = spread(p)
print(f"   pines repartidos sobre pistas a lo largo de cada lado ({n})")
