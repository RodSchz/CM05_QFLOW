#!/usr/bin/env python3
"""Vista de bloque del módulo generado (referencia para el floorplan).

Dibuja el contorno del chip con sus dimensiones y cada pin de E/S en su
posición real, con su nombre y una flecha según su dirección (entrada hacia
dentro, salida hacia fuera, bidireccional en ambos sentidos); vdd/gnd en gris.
Sin detalles del layout. Toma el contorno y los pines del DEF ruteado y las
direcciones del netlist.

Uso: block_view.py <diseno.def> <netlist.v> <salida.png> [salida.svg]
"""
import re, sys

def leer_def(path):
    t = open(path).read()
    escala = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", t).group(1))
    x0, y0, x1, y1 = (int(v) / escala for v in
                      re.search(r"DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", t).groups())
    nombre = re.search(r"^DESIGN (\S+)", t, re.M).group(1)
    pines = []
    for m in re.finditer(r"(?ms)^- (\S+) \+ NET \S+(.*?)\+ (?:PLACED|FIXED) \( (-?\d+) (-?\d+) \) \w+ ;",
                         re.search(r"(?ms)^PINS.*?^END PINS", t).group(0)):
        capa = re.search(r"LAYER (\w+)", m.group(2))
        pines.append((m.group(1), int(m.group(3)) / escala, int(m.group(4)) / escala,
                      capa.group(1) if capa else ""))
    return nombre, (x0, y0, x1, y1), pines


def direcciones(netlist):
    t = open(netlist).read()
    hdr = re.search(r"module\s+\w+\s*\((.*?)\);", t, re.S).group(1)
    d = {}
    for m in re.finditer(r"(input|output|inout)\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)", hdr):
        kind, msb, lsb, n = m.groups()
        if msb is None:
            d[n] = kind
        else:
            for i in range(min(int(msb), int(lsb)), max(int(msb), int(lsb)) + 1):
                d[f"{n}[{i}]"] = kind
    return d


def dibujar(defp, netp, png, svg=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyArrow
    nombre, (x0, y0, x1, y1), pines = leer_def(defp)
    dirs = direcciones(netp)
    W, H = x1 - x0, y1 - y0
    L = max(W, H)
    flecha = 0.06 * L                    # largo de las flechas
    fig, ax = plt.subplots(figsize=(10, 10 * max(H / W, 0.45) + 0.6))
    ax.add_patch(Rectangle((x0, y0), W, H, fill=True, fc="#eef3fb", ec="#1f3b73", lw=2))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, nombre, ha="center", va="center",
            fontsize=18, weight="bold", color="#1f3b73")
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 - 0.07 * H, f"{W:.0f} µm × {H:.0f} µm  ({W * H / 1e6:.2f} mm²)",
            ha="center", va="center", fontsize=11, color="#1f3b73")
    colores = {"input": "#1f77b4", "output": "#d62728", "inout": "#9467bd"}
    for n, px, py, capa in pines:
        dist = {"L": px - x0, "R": x1 - px, "B": py - y0, "T": y1 - py}
        lado = min(dist, key=dist.get)
        # punto sobre el borde
        bx = {"L": x0, "R": x1}.get(lado, px)
        by = {"B": y0, "T": y1}.get(lado, py)
        hacia_fuera = {"L": (-1, 0), "R": (1, 0), "B": (0, -1), "T": (0, 1)}[lado]
        es_pot = n in ("vdd", "gnd")
        kind = "power" if es_pot else dirs.get(n, "inout")
        col = "#7f7f7f" if es_pot else colores[kind]
        ox, oy = hacia_fuera
        ext_x, ext_y = bx + ox * flecha, by + oy * flecha
        hw, hl = 0.012 * L, 0.025 * L
        if kind == "input":
            ax.add_patch(FancyArrow(ext_x, ext_y, -ox * flecha, -oy * flecha, width=0.003 * L,
                                    head_width=hw, head_length=hl, length_includes_head=True, color=col))
        elif kind == "output":
            ax.add_patch(FancyArrow(bx, by, ox * flecha, oy * flecha, width=0.003 * L,
                                    head_width=hw, head_length=hl, length_includes_head=True, color=col))
        else:
            ax.plot([bx, ext_x], [by, ext_y], color=col, lw=2.5)
        ax.plot([bx], [by], marker="s", color=col, ms=5)
        tx, ty = bx + ox * (flecha + 0.012 * L), by + oy * (flecha + 0.012 * L)
        ha = {"L": "right", "R": "left"}.get(lado, "center")
        va = {"B": "top", "T": "bottom"}.get(lado, "center")
        rot = 90 if lado in "TB" else 0
        if lado in "TB":
            ha, va = "center", ("top" if lado == "B" else "bottom")
        ax.text(tx, ty, n, ha=ha, va=va, rotation=rot, fontsize=9, color=col,
                family="monospace", rotation_mode="anchor" if lado in "TB" else "default")
    m = flecha + 0.14 * L
    ax.set_xlim(x0 - m, x1 + m)
    ax.set_ylim(y0 - m, y1 + m)
    ax.set_aspect("equal")
    ax.set_xlabel("x (µm)"); ax.set_ylabel("y (µm)")
    ax.grid(alpha=0.2)
    from matplotlib.lines import Line2D
    leyenda = [Line2D([0], [0], color=colores["input"], lw=3, label="entrada"),
               Line2D([0], [0], color=colores["output"], lw=3, label="salida"),
               Line2D([0], [0], color="#7f7f7f", lw=3, label="alimentación")]
    if any(dirs.get(n) == "inout" for n, *_ in pines):
        leyenda.insert(2, Line2D([0], [0], color=colores["inout"], lw=3, label="bidireccional"))
    ax.legend(handles=leyenda, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    ax.set_title(f"{nombre} — vista de bloque (CIDESI_CM05)")
    fig.tight_layout()
    fig.savefig(png, dpi=130)
    if svg:
        fig.savefig(svg)
    return fig


if __name__ == "__main__":
    dibujar(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    print("   vista de bloque:", sys.argv[3])
