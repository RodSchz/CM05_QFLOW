#!/usr/bin/env bash
# Simulacion con Icarus Verilog de un diseno del flujo CM05_QFLOW.
#   rtl  : el Verilog fuente (source/<modulo>.v)
#   gate : el netlist post-ruteo que quedo en el layout (<modulo>_postroute.v)
#          con los modelos de celdas cm05 (simulacion funcional, sin retardos)
#   ambos: corre las dos y compara sus trazas de texto: deben ser identicas
# El testbench debe ser el modulo superior, guardar ondas con $dumpvars y
# reportar con $display; las lineas "RESULTADO:" se muestran al final.
# El VCD puede tener cualquier nombre ($dumpfile("dump.vcd") de EDA Playground,
# o ninguno): se deja siempre como sim_<rtl|gate>/sim.vcd.
# Uso: cm05_sim.sh <modulo> <dir_proyecto> <testbench.v> [rtl|gate|ambos] [PREFIX]
set -euo pipefail
MOD=$1; DIR=$(realpath "$2"); TB=$(realpath "$3"); MODO=${4:-ambos}; PREFIX=${5:-/opt/cm05_eda}
CELLS="$PREFIX/share/qflow/tech/cm05/cm05_stdcells.v"

sim() {   # sim <nombre> <archivos...>
    local d="$DIR/sim_$1"; shift
    mkdir -p "$d"
    iverilog -g2012 -o "$d/a.out" "$TB" "$@" 2> "$d/compila.log" || { cat "$d/compila.log"; return 1; }
    rm -f "$d"/*.vcd
    (cd "$d" && vvp -n a.out | grep -v "^VCD info" > salida.txt)
    # Normaliza el nombre del archivo de ondas a sim.vcd
    if [ ! -f "$d/sim.vcd" ]; then
        local v; v=$(ls -t "$d"/*.vcd 2>/dev/null | head -1 || true)
        if [ -n "$v" ]; then
            mv "$v" "$d/sim.vcd"
            echo "   (ondas: $(basename "$v") -> sim.vcd)"
        else
            echo "AVISO: el testbench no escribio ondas; agrega \$dumpvars(0, <tb>) para verlas"
        fi
    fi
    local n; n=$(ls "$d"/*.vcd 2>/dev/null | grep -vc '/sim.vcd$' || true)
    [ "${n:-0}" -gt 0 ] && echo "AVISO: el testbench escribio varios VCD; se usa sim.vcd" || true
}

if [[ $MODO == rtl || $MODO == ambos ]]; then
    echo "== Simulacion RTL ($MOD.v)"
    sim rtl "$DIR/source/$MOD.v"
    grep -E "^RESULTADO" "$DIR/sim_rtl/salida.txt" || tail -3 "$DIR/sim_rtl/salida.txt"
fi
if [[ $MODO == gate || $MODO == ambos ]]; then
    NET="$DIR/${MOD}_postroute.v"
    [ -f "$NET" ] || NET="$DIR/${MOD}.rtlnopwr.v"
    [ -f "$NET" ] || { echo "ERROR: no hay netlist sintetizado; corre primero cm05_flow.sh"; exit 1; }
    echo "== Simulacion a nivel compuertas ($(basename "$NET"))"
    # DEF2Verilog vuelve a declarar como wire los puertos ANSI; iverilog no lo acepta
    python3 -I - "$NET" "$DIR/${MOD}_gate_sim.v" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
hdr = re.search(r"module\s+\w+\s*\((.*?)\);", t, re.S)
ports = set(re.findall(r"(?:input|output|inout)\s+(?:\[[^\]]*\]\s*)?(\w+)", hdr.group(1))) if hdr else set()
t = re.sub(r"(?m)^\s*wire\s+(?:\[[^\]]*\]\s*)?(\w+)\s*;\s*\n", lambda m: "" if m.group(1) in ports else m.group(0), t)
open(sys.argv[2], "w").write(t)
PY
    sim gate "$DIR/${MOD}_gate_sim.v" "$CELLS"
    grep -E "^RESULTADO" "$DIR/sim_gate/salida.txt" || tail -3 "$DIR/sim_gate/salida.txt"
fi
if [[ $MODO == ambos ]]; then
    if diff -q "$DIR/sim_rtl/salida.txt" "$DIR/sim_gate/salida.txt" > /dev/null; then
        echo "== RTL y compuertas: trazas IDENTICAS"
    else
        echo "== RTL y compuertas: trazas DIFERENTES (primeras diferencias):"
        diff "$DIR/sim_rtl/salida.txt" "$DIR/sim_gate/salida.txt" | head -10
        exit 3
    fi
fi
# Modo estricto (pruebas automaticas): falla si algun testbench reporta errores
if [ "${CM05_STRICT:-0}" = 1 ] && grep -hq "^RESULTADO: .*ERROR" "$DIR"/sim_*/salida.txt; then exit 4; fi
