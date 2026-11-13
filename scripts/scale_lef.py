#!/usr/bin/env python3
"""Escala el LEF de osu050 (lambda 0.3 um) a CM05 (lambda 2.5 um) y lo
reduce a 2 metales.

- Multiplica por num/den toda la geometria (RECT, SIZE, PITCH, OFFSET, WIDTH,
  SPACING, OVERHANG, ORIGIN, FOREIGN, MANUFACTURINGGRID, SAMENET).
- RESISTANCE/CAPACITANCE se dejan intactos (no escalan con lambda; quedan como
  valores aproximados heredados de AMI C5).
- Elimina LAYER via2/metal3, VIA M3_M2, VIARULE viagen32/TURN3, sitios de pad,
  macros PAD*, y cualquier geometria de metal3/via2 dentro de macros.
- Elimina la regla SAMENET cc-via (CM05 prohibe via sobre contacto, regla 8.4).
- Opcional: --drop CELDA[,CELDA...] quita macros (celdas no soportadas).
Uso: scale_lef.py in.lef out.lef 25 3 [--drop A,B]
"""
import re, sys
from fractions import Fraction

src, dst = sys.argv[1], sys.argv[2]
k = Fraction(int(sys.argv[3]), int(sys.argv[4]))
drop_cells = set()
if "--drop" in sys.argv:
    drop_cells = set(sys.argv[sys.argv.index("--drop") + 1].split(","))

SCALE_KW = {"RECT", "SIZE", "PITCH", "OFFSET", "WIDTH", "SPACING", "OVERHANG",
            "METALOVERHANG", "ORIGIN", "FOREIGN", "MANUFACTURINGGRID", "SAMENET"}
DROP_LAYERS = {"via2", "metal3"}
num_re = re.compile(r"-?\d+\.\d+|-?\d+")

def scale_line(line):
    toks = line.split()
    if not toks or toks[0] not in SCALE_KW:
        return line
    def rep(m):
        v = Fraction(m.group(0)) * k
        return f"{float(v):.3f}"
    if toks[0] == "FOREIGN":       # FOREIGN <nombre> x y ;
        head, name, rest = line.split(None, 2)
        lead = line[: len(line) - len(line.lstrip())]
        return f"{lead}{head} {name} " + num_re.sub(rep, rest)
    if toks[0] == "SAMENET":       # SAMENET l1 l2 valor ;
        lead = line[: len(line) - len(line.lstrip())]
        return lead + " ".join(toks[:3]) + " " + num_re.sub(rep, " ".join(toks[3:])) + "\n"
    return num_re.sub(rep, line)

lines = open(src).read().splitlines(keepends=True)
out, i = [], 0
skip_until = None          # texto END que cierra un bloque descartado
in_macro = False
skip_geom = False          # dentro de PORT/OBS tras "LAYER metal3 ;"
while i < len(lines):
    ln = lines[i]; t = ln.split()
    i += 1
    if skip_until:
        if t[:2] == ["END", skip_until]:
            skip_until = None
        continue
    if not t:
        out.append(ln); continue
    kw = t[0]
    # bloques de nivel superior a descartar
    if not in_macro and kw == "LAYER" and len(t) > 1 and t[1] in DROP_LAYERS:
        skip_until = t[1]; continue
    if kw == "VIA" and t[1] == "M3_M2":
        skip_until = "M3_M2"; continue
    if kw == "VIARULE" and t[1] in ("viagen32", "TURN3"):
        skip_until = t[1]; continue
    if kw == "SITE" and not in_macro and t[1] in ("corner", "IO"):
        skip_until = t[1]; continue
    if kw == "SAMENET":            # ambas reglas SAMENET (cc-via y via-via2)
        continue
    if kw == "MACRO":
        if t[1].startswith("PAD") or t[1] in drop_cells:
            skip_until = t[1]; continue
        in_macro = True; out.append(ln); continue
    if in_macro and kw == "END" and len(t) > 1 and t[1] not in ("PORT",) and not ln.startswith(" "):
        in_macro = False
    # geometria dentro de macros
    if kw == "LAYER" and len(t) > 1:
        lname = t[1]
        skip_geom = lname in DROP_LAYERS
        if skip_geom:
            continue
    elif kw in ("END",):
        skip_geom = False
    elif skip_geom and kw in ("RECT", "POLYGON"):
        continue
    if kw == "MANUFACTURINGGRID":
        out.append(f"MANUFACTURINGGRID {float(Fraction('0.15')*k):.3f} ;\n"); continue
    out.append(scale_line(ln))

hdr = ("# CM05: LEF escalado desde osu050 (OSU, AMI C5) por factor "
       f"{k} -> lambda = 2.5 um, 2 metales.\n"
       "# RESISTANCE/CAPACITANCE heredados de AMI C5: APROXIMADOS, no medidos en CM05.\n")
txt = "".join(out).replace("SPACING\nEND SPACING\n", "")
open(dst, "w").write(hdr + txt)
