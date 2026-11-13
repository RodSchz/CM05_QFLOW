#!/usr/bin/env python3
"""Extrae transistores y conectividad de dos GDS de la misma celda (reglas de
conexion de CIDESI_CM05: activo/poly/contactos 47-48/M1/Via/M2) y compara los
netlists. Sirve para confirmar que una edicion de layout no cambio el circuito.
Uso: netcompare.py a.gds b.gds CELDA"""
import sys, klayout.db as db

def extract(path, cell):
    ly = db.Layout(); ly.read(path)
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, ly.cell(cell), []))
    g = lambda l: l2n.make_layer(ly.layer(l, 0), str(l))
    nw, aa, pl, nsel, psel, ctp, cta, m1, v1, m2 = (g(x) for x in (42, 43, 46, 45, 44, 47, 48, 49, 50, 51))
    pact = aa & nw & psel; nact = (aa - nw) & nsel
    pg = pact & pl; ng = nact & pl
    psd = pact - pg; nsd = nact - ng
    for n, lr in (("psd", psd), ("nsd", nsd), ("pg", pg), ("ng", ng)):
        l2n.register(lr, n)
    # MOS de 3 terminales: el bulk no cambia con ediciones de vias/metal
    l2n.extract_devices(db.DeviceExtractorMOS3Transistor("P"), {"SD": psd, "G": pg, "tS": psd, "tD": psd, "tG": pl})
    l2n.extract_devices(db.DeviceExtractorMOS3Transistor("N"), {"SD": nsd, "G": ng, "tS": nsd, "tD": nsd, "tG": pl})
    for a, b in ((psd, cta), (nsd, cta), (pl, ctp), (cta, m1), (ctp, m1), (m1, v1), (v1, m2)):
        l2n.connect(a, b)
    l2n.connect(pl); l2n.connect(m1); l2n.connect(m2); l2n.connect(psd); l2n.connect(nsd)
    l2n.extract_netlist()
    nl = l2n.netlist(); nl.purge(); nl.combine_devices()
    return l2n, ly   # mantener vivos: el netlist pertenece a l2n

ka, kb = extract(sys.argv[1], sys.argv[3]), extract(sys.argv[2], sys.argv[3])
a, b = ka[0].netlist(), kb[0].netlist()
ca, cb = a.circuit_by_name(sys.argv[3]), b.circuit_by_name(sys.argv[3])
print(f"A: {len(list(ca.each_device()))} transistores, {len(list(ca.each_net()))} redes | B: {len(list(cb.each_device()))} transistores, {len(list(cb.each_net()))} redes")
ok = db.NetlistComparer().compare(a, b)
# W/L de todos los transistores (en toda la jerarquia): deben coincidir
def wl(nl):
    return sorted((d.device_class().name, round(d.parameter("W"), 3), round(d.parameter("L"), 3))
                  for c in nl.each_circuit() for d in c.each_device())
if wl(a) != wl(b):
    print("W/L DIFERENTES"); ok = False
print("NETLISTS EQUIVALENTES" if ok else "NETLISTS DIFERENTES")
sys.exit(0 if ok else 1)
