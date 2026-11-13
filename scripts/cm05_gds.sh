#!/usr/bin/env bash
# Genera el GDS final de un diseno ruteado por qflow con tecnologia cm05.
# Sustituye a la etapa "qflow gdsii", que se niega a correr si el DRC de magic
# (hecho sobre vistas abstractas LEF) reporta errores. El DRC de referencia es
# el de KLayout (cm05_drc.sh).
# Uso: cm05_gds.sh <modulo> [dir_layout] [PREFIX]
set -euo pipefail
MOD=$1
LAYDIR=${2:-.}
PREFIX=${3:-/opt/cm05_eda}
TECH="$PREFIX/share/qflow/tech/cm05"
cd "$LAYDIR"
cat > "gds_${MOD}.tcl" <<EOF
tech load $TECH/CM05.tech -noprompt
drc off
box 0 0 0 0
gds readonly true
gds rescale false
gds read $TECH/cm05_stdcells.gds
load $MOD
select top cell
expand
cif *hier write disable
cif *array write disable
gds write $MOD
quit -noprompt
EOF
[ -f "$TECH/cm05_stdcells.gds" ] || { echo "No existe $TECH/cm05_stdcells.gds"; exit 1; }
magic -dnull -noconsole "gds_${MOD}.tcl" > "gds_${MOD}.log" 2>&1
if grep -qE "Cannot open|couldn't be read|is unavailable" "gds_${MOD}.log"; then
    echo "ERROR: magic no pudo cargar celdas; ver gds_${MOD}.log"; exit 1
fi
ls -l "${MOD}.gds"
