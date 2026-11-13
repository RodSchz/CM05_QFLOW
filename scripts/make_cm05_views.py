#!/usr/bin/env python3
"""Genera las vistas SPICE y liberty de CM05 a partir de las de osu050.

SPICE: escala w, l (x k), ad/as (x k^2), pd/ps (x k) para que el LVS de netgen
       compare contra el layout escalado.
Liberty: elimina las celdas excluidas, escala 'area' por k^2 y marca el archivo
       como APROXIMADO: tiempos y capacitancias son de AMI C5 a 0.5 um, no de CM05.
Uso: make_cm05_views.py osu.sp osu.lib out.sp out.lib 25 3 --drop A,B,...
"""
import re, sys
from fractions import Fraction

sp_in, lib_in, sp_out, lib_out = sys.argv[1:5]
k = Fraction(int(sys.argv[5]), int(sys.argv[6]))
drop = set(sys.argv[sys.argv.index("--drop") + 1].split(",")) if "--drop" in sys.argv else set()

def fmt(x):
    return f"{float(x):.6g}"

# ---------------- SPICE ----------------
def sp_param(m):
    key, val, unit = m.group(1).lower(), Fraction(m.group(2)), m.group(3)
    f = {"w": k, "l": k, "pd": k, "ps": k, "ad": k * k, "as": k * k}[key]
    return f"{m.group(1)}={fmt(val * f)}{unit}"

sp = open(sp_in).read()
sp = re.sub(r"\b(w|l|ad|as|pd|ps)=([0-9.]+)([a-zA-Z]*)", sp_param, sp)
hdr = (f"* CM05: netlist de celdas OSU escalado x{k} (lambda 2.5 um).\n"
       "* nfet/pfet son los nombres de dispositivo que extrae magic; para simular\n"
       "* con los modelos de CIDESI_CM05 mapear a CIDNMOS/CIDPMOS.\n")
open(sp_out, "w").write(hdr + sp)

# ---------------- Liberty ----------------
lib = open(lib_in).read()
out, i = [], 0
cell_re = re.compile(r"\n(\s*)cell\s*\(\s*\"?(\w+)\"?\s*\)\s*\{")
while True:
    m = cell_re.search(lib, i)
    if not m:
        out.append(lib[i:]); break
    name = m.group(2)
    # buscar la llave de cierre de la celda
    j, depth = m.end(), 1
    while depth:
        c = lib[j]
        depth += (c == "{") - (c == "}")
        j += 1
    if name in drop or name.startswith("PAD"):
        out.append(lib[i:m.start()])
    else:
        out.append(lib[i:j])
    i = j
lib = "".join(out)
lib = re.sub(r"(\barea\s*:\s*)([0-9.]+)", lambda mm: mm.group(1) + fmt(Fraction(mm.group(2)) * k * k), lib)
lib = re.sub(r"library\s*\(\s*osu05_stdcells\s*\)", "library(cm05_osu_approx)", lib, count=1)
hdr = ("/* ======================================================================\n"
       " * cm05_stdcells.lib  --  LIBERTY APROXIMADO, NO CARACTERIZADO EN CM05\n"
       f" * Derivado de osu05_stdcells.lib (AMI C5, 0.5 um). Areas escaladas x{k*k};\n"
       " * tiempos, capacitancias y potencias SIN cambio: solo sirven para que\n"
       " * yosys/abc mapeen la logica, no para estimar desempeno de CM05.\n"
       f" * Celdas excluidas (violan regla 8.5 de CM05): {', '.join(sorted(drop)) or 'ninguna'}\n"
       " * ====================================================================== */\n")
open(lib_out, "w").write(hdr + lib)
