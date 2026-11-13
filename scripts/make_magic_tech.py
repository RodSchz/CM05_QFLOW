#!/usr/bin/env python3
"""Genera CM05.tech (magic) a partir de SCN3ME_SUBM.30.tech.

- Conserva un solo estilo de salida y uno de entrada GDS: lambda=2.5(p),
  con scalefactor 250 centimicras (lambda = 2.5 um).
- En la salida GDS elimina capas que CM05 no tiene o que chocan con su mapa
  (61 Via2, 62 Metal3, 81-83 pines auxiliares, 100-103/109/110/119 relleno;
  100/0 en CM05 es Die.outline).
- Las reglas DRC de magic se quedan en lambda (mismo juego SCMOS SUBM), pero el
  DRC de referencia es el deck de KLayout de CIDESI_CM05.
Uso: make_magic_tech.py SCN3ME_SUBM.30.tech CM05.tech
"""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
DROP_OUT = {"64", "65", "66", "67", "68", "71", "72", "73", "61", "62", "81", "82", "83", "100", "101", "102", "103", "109", "110", "119"}

def section(name):
    m = re.search(rf"^{name}\n(.*?)^end\n", text, re.S | re.M)
    return m

def styles(body):
    parts = re.split(r"(?m)^(?=style\s)", body)
    return parts[0], parts[1:]

def drop_layers(style_text):
    # bloques "layer X ...\n ... calma N 0\n" -> se eliminan si N en DROP_OUT
    lines = style_text.splitlines(keepends=True)
    out, buf = [], []
    for ln in lines:
        t = ln.split()
        if t[:1] in (["layer"], ["templayer"]) and buf:
            out.extend(buf); buf = []
        if t[:1] in (["layer"], ["templayer"]):
            buf = [ln]; continue
        if buf:
            buf.append(ln)
            if t[:1] == ["calma"]:
                if t[1] not in DROP_OUT:
                    out.extend(buf)
                buf = []
            continue
        out.append(ln)
    out.extend(buf)
    return "".join(out)

SCALED_OPS = {"grow", "shrink", "squares", "squares-grid", "bloat-or", "bloat-and",
              "bloat-min", "bloat-max", "grow-min", "grow-grid", "slots", "bridge"}
K_NUM, K_DEN = 25, 3   # 0.30 um -> 2.5 um por lambda

def scale_rules(style_text):
    """Las distancias de reglas cif (grow, squares, bloat...) estan en
    centimicras absolutas, no en lambda: hay que escalarlas igual que la
    geometria, o los cortes saldrian del tamano de AMI (0.6 um)."""
    out = []
    for ln in style_text.splitlines(keepends=True):
        t = ln.split()
        if t and t[0] in SCALED_OPS:
            new = []
            for tok in t:
                if tok.isdigit():
                    v = int(tok) * K_NUM
                    assert v % K_DEN == 0, ln
                    new.append(str(v // K_DEN))
                else:
                    new.append(tok)
            lead = ln[: len(ln) - len(ln.lstrip())]
            ln = lead + " ".join(new) + "\n"
        out.append(ln)
    return "".join(out)

for name, sf_new, dropper in (("cifoutput", "250 125", drop_layers), ("cifinput", "250", None)):
    m = section(name)
    head, sts = styles(m.group(1))
    keep = [s for s in sts if s.split()[1] == "lambda=0.30(p)"][0]
    keep = keep.replace("lambda=0.30(p)", "lambda=2.5(p)", 1)
    keep = re.sub(r"(?m)^(\s*scalefactor\s+).*$", lambda mm: mm.group(1) + sf_new, keep, count=1)
    keep = scale_rules(keep)
    if dropper:
        keep = dropper(keep)
    text = text[: m.start(1)] + head + keep + text[m.end(1):]

# extraccion: centimicras por lambda (afecta W/L extraidos para LVS)
m = section("extract")
text = text[: m.start(1)] + re.sub(r"(?m)^(\s*lambda\s+)30\b", r"\g<1>250", m.group(1)) + text[m.end(1):]

text = text.replace("tech\n  format 29\n scmos\n", "tech\n  format 29\n CM05\n", 1)
text = ("# CM05.tech: derivado de SCN3ME_SUBM.30.tech (OSU) para CIDESI_CM05, lambda = 2.5 um.\n"
        "# Parasiticos de extraccion heredados de AMI C5: APROXIMADOS.\n") + text
open(dst, "w").write(text)
