#!/usr/bin/env bash
# Corre el deck DRC oficial de CIDESI_CM05 (KLayout) sobre un GDS y resume.
# Uso: cm05_drc.sh <archivo.gds> <topcell> <drc.lydrc>
set -euo pipefail
GDS=$1; TOP=$2; DECK=$3
OUT="${GDS%.gds}_drc.lyrdb"
QT_QPA_PLATFORM=offscreen klayout -b -r "$DECK" \
    -rd input="$GDS" -rd topcell="$TOP" -rd output="$OUT" > "${GDS%.gds}_drc.log" 2>&1
python3 -I "$(dirname "$0")/rdb_summary.py" "$OUT"
