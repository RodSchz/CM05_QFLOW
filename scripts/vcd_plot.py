#!/usr/bin/env python3
"""Dibuja formas de onda de un archivo VCD (Icarus Verilog) con matplotlib.

Senales de 1 bit como trazo digital; buses como bandas con su valor (hex o
decimal). Por omision muestra las senales del modulo superior del testbench.

Uso como script: vcd_plot.py sim.vcd salida.png [senal,senal,...] [t0_ns t1_ns]
Uso desde Python: from vcd_plot import read_vcd, plot
"""
import re, sys


def read_vcd(path):
    """Devuelve (timescale_str, {nombre: (ancho, [(t, valor_str), ...])}).
    Los nombres llevan la jerarquia: 'tb.q', 'tb.dut.q'."""
    sigs, ids, scope, ts = {}, {}, [], "1s"
    t = 0
    with open(path) as f:
        defs = True
        for line in f:
            tok = line.split()
            if not tok:
                continue
            if defs:
                if tok[0] == "$timescale":
                    rest = " ".join(tok[1:]).replace("$end", "").strip() or next(f).strip()
                    ts = rest
                elif tok[0] == "$scope":
                    scope.append(tok[2])
                elif tok[0] == "$upscope":
                    scope.pop()
                elif tok[0] == "$var":
                    width, code, name = int(tok[2]), tok[3], tok[4]
                    full = ".".join(scope + [name])
                    sigs[full] = (width, [])
                    ids.setdefault(code, []).append(full)
                elif tok[0] == "$enddefinitions":
                    defs = False
                continue
            c = tok[0]
            if c[0] == "#":
                t = int(c[1:])
            elif c[0] in "bBrR":
                for n in ids.get(tok[1], []):
                    sigs[n][1].append((t, c[1:]))
            elif c[0] in "01xXzZ" and len(c) > 1:
                for n in ids.get(c[1:], []):
                    sigs[n][1].append((t, c[0]))
    return ts, sigs


def _to_ns(ts):
    """Factor para pasar unidades del VCD a ns ('1ps' -> 0.001)."""
    m = re.match(r"\s*(\d+)\s*(s|ms|us|ns|ps|fs)", ts)
    if not m:
        return 1.0
    return int(m.group(1)) * {"s": 1e9, "ms": 1e6, "us": 1e3, "ns": 1.0, "ps": 1e-3, "fs": 1e-6}[m.group(2)]


def _fmt(v, width, radix):
    if any(ch in v.lower() for ch in "xz"):
        return "x"
    n = int(v, 2)
    return f"{n:X}" if radix == "hex" else str(n)


def plot(path, signals=None, t0=None, t1=None, radix="hex", out=None, ax=None):
    """t0 y t1 en ns."""
    import matplotlib
    if out:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ts, sigs = read_vcd(path)
    k = _to_ns(ts)                      # todo se dibuja en ns
    for n in sigs:
        w, ch = sigs[n]
        sigs[n] = (w, [(tt * k, v) for tt, v in ch])
    if not signals:
        top = min((n.split(".")[0] for n in sigs), default="")
        signals = [n for n in sigs if n.count(".") == 1 and n.startswith(top + ".")]
    else:
        signals = [s if s in sigs else next((n for n in sigs if n.endswith("." + s)), s) for s in signals]
    signals = [s for s in signals if s in sigs and sigs[s][1]]
    tend = max(ch[-1][0] for _, ch in (sigs[s] for s in signals))
    t0 = 0 if t0 is None else t0
    t1 = tend if t1 is None else t1
    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 0.55 * len(signals) + 1))
    for row, name in enumerate(signals):
        width, ch = sigs[name]
        y = len(signals) - 1 - row
        pts = [(tt, v) for tt, v in ch if tt <= t1]
        segs = []
        for i, (tt, v) in enumerate(pts):
            te = pts[i + 1][0] if i + 1 < len(pts) else t1
            a, b = max(tt, t0), min(te, t1)
            if b > a or (b == a == t1):
                segs.append((a, b, v))
        if width == 1:
            xs, ys = [], []
            for a, b, v in segs:
                lvl = {"1": 0.8, "0": 0.0}.get(v, 0.4)
                xs += [a, b]; ys += [y + lvl, y + lvl]
                if v not in "01":
                    ax.fill_between([a, b], y, y + 0.8, color="#d62728", alpha=0.3, lw=0)
            ax.plot(xs, ys, color="#1f77b4", lw=1.2, drawstyle="default")
        else:
            for a, b, v in segs:
                col = "#d62728" if "x" in v.lower() else "#2ca02c"
                ax.fill_between([a, b], y + 0.1, y + 0.7, color=col, alpha=0.25, lw=0)
                ax.plot([a, b], [y + 0.1, y + 0.1], color=col, lw=0.8)
                ax.plot([a, b], [y + 0.7, y + 0.7], color=col, lw=0.8)
                ax.plot([a, a], [y + 0.1, y + 0.7], color=col, lw=0.8)
                if (b - a) > (t1 - t0) / 60:
                    ax.text((a + b) / 2, y + 0.4, _fmt(v, width, radix), ha="center", va="center", fontsize=8)
    ax.set_yticks([len(signals) - 1 - i + 0.4 for i in range(len(signals))])
    ax.set_yticklabels([s.split(".", 1)[1] + (f"[{sigs[s][0]-1}:0]" if sigs[s][0] > 1 else "") for s in signals])
    ax.set_xlim(t0, t1)
    ax.set_xlabel("tiempo (ns)")
    ax.grid(axis="x", alpha=0.3)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    if fig is not None:
        fig.tight_layout()
        if out:
            fig.savefig(out, dpi=110)
    return ax


if __name__ == "__main__":
    vcd, png = sys.argv[1], sys.argv[2]
    sel = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else None
    a = float(sys.argv[4]) if len(sys.argv) > 4 else None
    b = float(sys.argv[5]) if len(sys.argv) > 5 else None
    plot(vcd, sel, a, b, out=png)
    print("formas de onda:", png)
