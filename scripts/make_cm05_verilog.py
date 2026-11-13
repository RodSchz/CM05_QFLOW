#!/usr/bin/env python3
"""Genera cm05_stdcells.v (modelos Verilog para simulacion a nivel compuertas)
a partir de osu05_stdcells.v: elimina solo los modulos de celdas que no existen
en cm05 (excluidas por la regla 8.5 y pads); las primitivas (udp_*) y todo lo
demas se conservan.
Los retardos de los bloques specify son de AMI C5: la simulacion por omision
es funcional (iverilog los ignora sin -gspecify).
Uso: make_cm05_verilog.py osu05_stdcells.v cm05_stdcells.lib out.v"""
import re, sys
src, lib, out = sys.argv[1:4]
cells = set(re.findall(r"^\s*cell\s*\(\s*\"?(\w+)", open(lib).read(), re.M)) | {"FILL"}
txt = open(src).read()
mods = re.findall(r"(?m)^module\s+(\w+)", txt)
dropped = [m for m in mods if m not in cells]
for m in dropped:
    txt = re.sub(rf"(?ms)(^`timescale[^\n]*\n)?(^`celldefine\n)?^module\s+{m}\b.*?^endmodule[^\n]*\n(^`endcelldefine\n)?",
                 "", txt, count=1)
assert not set(re.findall(r"(?m)^module\s+(\w+)", txt)) - cells
hdr = ("// cm05_stdcells.v -- modelos funcionales de la biblioteca cm05 (CIDESI_CM05)\n"
       "// Derivado de osu05_stdcells.v (OSU). Retardos de specify: AMI C5, NO de CM05.\n"
       f"// Celdas omitidas (no disponibles en cm05): {', '.join(dropped)}\n")
open(out, "w").write(hdr + txt)
print(f"{out}: {len(mods) - len(dropped)} modulos, omitidos {len(dropped)}, "
      f"primitivas {len(re.findall(r'(?m)^primitive', txt))}")
