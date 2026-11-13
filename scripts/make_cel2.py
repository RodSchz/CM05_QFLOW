#!/usr/bin/env python3
"""Genera <modulo>.cel2 (posición de pines de E/S para graywolf/qflow) a partir
de una especificación sencilla por lado.

Especificación (JSON):
    {"izquierda": ["clk", "rst"], "abajo": ["en"], "derecha": ["q"],
     "arriba": [], "orden_fijo": false}
- Un nombre de bus sin índice ('q') se expande a todos sus bits según los
  puertos del netlist sintetizado (q[0] ... q[7]).
- Los pines que no se mencionan quedan libres (graywolf los coloca).
- orden_fijo = true conserva el orden de la lista en cada lado; si es false,
  graywolf puede permutarlos dentro del lado para acortar el ruteo.

Uso: make_cel2.py <netlist.rtlnopwr.v> <especificacion.json> <salida.cel2>
"""
import json, re, sys

net, spec_path, out = sys.argv[1:4]
spec = json.load(open(spec_path))
txt = open(net).read()
hdr = re.search(r"module\s+\w+\s*\((.*?)\);", txt, re.S).group(1)
puertos = {}                       # nombre -> lista de bits
for m in re.finditer(r"(input|output|inout)\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)", hdr):
    _, msb, lsb, name = m.groups()
    if msb is None:
        puertos[name] = [name]
    else:
        a, b = int(msb), int(lsb)
        rng = range(min(a, b), max(a, b) + 1)
        puertos[name] = [f"{name}[{i}]" for i in rng]
todos = {b for bits in puertos.values() for b in bits}

LADOS = {"izquierda": "L", "derecha": "R", "arriba": "T", "abajo": "B"}
usados, bloques, errores = set(), [], []
for lado, letra in LADOS.items():
    nombres = spec.get(lado) or []
    bits = []
    for n in nombres:
        if n in puertos:
            bits += puertos[n]
        elif n in todos:
            bits.append(n)
        else:
            errores.append(n)
    for b in bits:
        if b in usados:
            errores.append(f"{b} (repetido)")
        usados.add(b)
    if bits:
        modo = "nopermute" if spec.get("orden_fijo") else "permute"
        bloques.append(f"padgroup pines_{lado} {modo}\n" + "".join(f"twpin_{b} fixed\n" for b in bits)
                       + f"restrict side {letra}\n")
if errores:
    sys.exit("ERROR en PINES: no existen " + ", ".join(errores)
             + "\n  puertos del diseño: " + ", ".join(p for p in puertos if p not in ("vdd", "gnd")))
open(out, "w").write("\n".join(bloques))
libres = sorted(todos - usados - {"vdd", "gnd"})
n_lados = sum(len(puertos.get(n, [n])) for lado in ("izquierda", "derecha") for n in (spec.get(lado) or []))
if n_lados:
    print(f"AVISO: {n_lados} pines a izquierda/derecha. Con 2 metales esos pines (metal1) compiten con las"
          " franjas de alimentacion de los costados y el ruteo puede no cerrar; prefiere arriba/abajo.")
print(f"posición de pines: {len(usados)} fijados por lado" + (f"; libres: {', '.join(libres)}" if libres else ""))
