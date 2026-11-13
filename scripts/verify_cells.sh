#!/usr/bin/env bash
# Verifica celdas de la biblioteca: DRC del deck CM05 y netlist igual al original.
# Uso: verify_cells.sh lib_nueva.gds lib_original.gds drc.lydrc CELDA [CELDA...]
set -uo pipefail
NEW=$1; ORIG=$2; DECK=$3; shift 3
S=$(cd "$(dirname "$0")" && pwd)
W=$(mktemp -d)
fail=0
for c in "$@"; do
  for f in NEW ORIG; do
    python3 -I - "${!f}" "$c" "$W/${c}_$f.gds" <<'PY'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1])
o = db.Layout(); o.dbu = ly.dbu
o.create_cell(sys.argv[2]).copy_tree(ly.cell(sys.argv[2])); o.write(sys.argv[3])
PY
  done
  QT_QPA_PLATFORM=offscreen klayout -b -r "$DECK" -rd input="$W/${c}_NEW.gds" -rd topcell="$c" -rd output="$W/$c.lyrdb" >/dev/null 2>&1
  n=$(python3 -I "$S/rdb_summary.py" "$W/$c.lyrdb" | awk '/TOTAL/{print $2}')
  eq=$(python3 -I "$S/netcompare.py" "$W/${c}_ORIG.gds" "$W/${c}_NEW.gds" "$c" | tail -1)
  printf "%-10s DRC=%-3s %s\n" "$c" "$n" "$eq"
  [ "$n" = "0" ] && [ "$eq" = "NETLISTS EQUIVALENTES" ] || fail=1
done
rm -rf "$W"
exit $fail
