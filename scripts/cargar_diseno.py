#!/usr/bin/env python3
"""Organiza los archivos Verilog de un diseño para el flujo CM05_QFLOW.

Recibe los .v (diseño, submódulos y testbench, en uno o varios archivos) y,
opcionalmente, un .cel2 de posición de pines. Detecta:
  - el testbench: archivos *_tb.v / tb_*.v, o los que solo definen módulos sin puertos;
  - el módulo superior: el módulo de diseño que ningún otro instancia (si hay
    varios, el que instancia el testbench).
Escribe en la carpeta de diseño <top>.v (todo el diseño), <top>_tb.v (testbench)
y <top>.cel2 si se dio uno. Devuelve el nombre del módulo superior.

Uso: cargar_diseno.py <carpeta_diseno> archivo.v [archivo.v ...] [pines.cel2]
"""
import pathlib, re, sys

COMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def modulos(texto):
    """[(nombre, tiene_puertos, cuerpo)] de cada module ... endmodule."""
    t = COMENT.sub("", texto)
    out = []
    for m in re.finditer(r"\bmodule\s+(\w+)\s*(#\s*\(.*?\)\s*)?(\(|;)(.*?)\bendmodule\b", t, re.S):
        nombre, _, sep, cuerpo = m.groups()
        puertos = sep == "(" and not re.match(r"\s*\)\s*;", cuerpo)
        out.append((nombre, puertos, cuerpo))
    return out


def instancias(cuerpo, conocidos):
    return {n for n in re.findall(r"\b(\w+)\s+(?:#\s*\(.*?\)\s*)?\w+\s*\(", cuerpo, re.S) if n in conocidos}


def preparar(archivos, destino):
    destino = pathlib.Path(destino); destino.mkdir(parents=True, exist_ok=True)
    archivos = [pathlib.Path(a) for a in archivos]
    vs = [a for a in archivos if a.suffix.lower() in (".v", ".sv")]
    cel2 = [a for a in archivos if a.suffix.lower() == ".cel2"]
    if not vs:
        raise SystemExit("No se recibió ningún archivo .v")
    info = {a: modulos(a.read_text(errors="ignore")) for a in vs}
    for a, mods in info.items():
        if not mods:
            raise SystemExit(f"{a.name}: no se encontró ningún 'module ... endmodule'")
    es_tb = {a: bool(re.search(r"(_tb|^tb_|_test)\.s?v$", a.name, re.I)) or all(not p for _, p, _ in m)
             for a, m in info.items()}
    tbs = [a for a in vs if es_tb[a]]
    dis = [a for a in vs if not es_tb[a]]
    if not dis:
        raise SystemExit("Solo se recibieron testbenches; falta el archivo del diseño")
    mods_dis = {n: c for a in dis for n, _, c in info[a]}
    usados = set().union(*(instancias(c, mods_dis) - {n} for n, c in mods_dis.items()))
    cand = [n for n in mods_dis if n not in usados]
    if len(cand) > 1 and tbs:
        en_tb = set().union(*(instancias(c, mods_dis) for a in tbs for _, _, c in info[a]))
        cand = [n for n in cand if n in en_tb] or cand
    if len(cand) != 1:
        raise SystemExit(f"No se pudo decidir el módulo superior entre: {', '.join(cand)}")
    top = cand[0]
    (destino / f"{top}.v").write_text("\n".join(a.read_text(errors="ignore") for a in dis))
    if tbs:
        (destino / f"{top}_tb.v").write_text("\n".join(a.read_text(errors="ignore") for a in tbs))
        if not any(top in instancias(c, {top}) for a in tbs for _, _, c in info[a]):
            print(f"AVISO: el testbench no instancia a '{top}'")
    else:
        print(f"AVISO: no se recibió testbench; agrega uno (<{top}>_tb.v) para poder simular")
    if cel2:
        (destino / f"{top}.cel2").write_text(cel2[0].read_text())
    print(f"Módulo superior: {top}  |  diseño: {', '.join(a.name for a in dis)}"
          + (f"  |  testbench: {', '.join(a.name for a in tbs)}" if tbs else "")
          + (f"  |  pines: {cel2[0].name}" if cel2 else ""))
    return top


if __name__ == "__main__":
    preparar(sys.argv[2:], sys.argv[1])
