#!/usr/bin/env python3
"""Actualiza 'area' de cada celda del liberty con SIZE (ancho x alto) del LEF.
Uso: lib_areas_from_lef.py lib.lef lib.lib"""
import re, sys
lef, lib = sys.argv[1], sys.argv[2]
size = {m: float(w) * float(h) for m, w, h in
        re.findall(r"(?ms)^MACRO (\w+)\n.*?SIZE ([\d.]+) BY ([\d.]+)", open(lef).read())}
s = open(lib).read()
def rep(m):
    return m.group(1) + f"{size[m.group(2)]:g}" if m.group(2) in size else m.group(0)
s = re.sub(r"(cell\s*\(\s*\"?(\w+)\"?\s*\)\s*\{\s*area\s*:\s*)[0-9.]+", lambda m: rep(m), s)
open(lib, "w").write(s)
