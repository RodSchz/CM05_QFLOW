#!/usr/bin/env bash
# Construye tech/cm05 completo a partir de la tecnologia osu050 de qflow.
# Uso: [DECK=ruta/drc.lydrc] build_cm05_tech.sh <dir_osu050> [salida=tech/cm05]
# Con DECK definido verifica cada celda (DRC CM05 + netlist + W/L).
set -euo pipefail
OSU=$1
HERE=$(cd "$(dirname "$0")/.." && pwd)
OUT=${2:-$HERE/tech/cm05}
S=$HERE/scripts
TMP=$(mktemp -d)
K="25 3"                                  # lambda 0.30 -> 2.5 um
EXCLUIDAS=DFFSR,DFFNEGX1,LATCH,XOR2X1,XNOR2X1,FAX1,HAX1   # violan regla 8.5
mkdir -p "$OUT"

echo "== 1. GDS de celdas escalado (sin capas auxiliares 81/109 de magic)"
python3 -I $S/scale_gds.py "$OSU/osu05_stdcells.gds2" "$OUT/cm05_stdcells.gds" $K 1.25 --strip 81/0,109/0

echo "== 2. LEF escalado, 2 metales"
python3 -I $S/scale_lef.py "$OSU/osu050_stdcells.lef" "$OUT/cm05_stdcells.lef" $K

echo "== 3. SPICE y liberty (aproximado)"
python3 -I $S/make_cm05_views.py "$OSU/osu050_stdcells.sp" "$OSU/osu05_stdcells.lib" \
    "$OUT/cm05_stdcells.sp" "$OUT/cm05_stdcells.lib" $K --drop $EXCLUIDAS

echo "== 3b. Modelos Verilog de celdas (simulacion a nivel compuertas)"
python3 -I $S/make_cm05_verilog.py "$OSU/osu05_stdcells.v" "$OUT/cm05_stdcells.lib" "$OUT/cm05_stdcells.v"

echo "== 4. Tech de magic"
python3 -I $S/make_magic_tech.py "$OSU/SCN3ME_SUBM.30.tech" "$OUT/CM05.tech"

echo "== 5. DFFPOSX1: regla 8.5 (vias lejos de bordes de poly/activo)"
python3 -I - "$OUT/cm05_stdcells.gds" "$TMP/dff.gds" <<'EOF'
import sys, klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1])
out = db.Layout(); out.dbu = ly.dbu
out.create_cell("DFFPOSX1").copy_tree(ly.cell("DFFPOSX1"))
out.write(sys.argv[2])
EOF
CORTES=$(python3 -I $S/fix_cell_vias.py "$TMP/dff.gds" DFFPOSX1 "$TMP/dff3.gds" 240 | tee /dev/stderr | sed -n 's/^CORTES: //p' | tr ' ' ',')
python3 -I $S/netcompare.py "$TMP/dff.gds" "$TMP/dff3.gds" DFFPOSX1
python3 -I $S/apply_cell_fix.py "$OUT/cm05_stdcells.gds" "$OUT/cm05_stdcells.lef" "$TMP/dff3.gds" DFFPOSX1 "$CORTES" 20

echo "== 6. Acceso a pines: via legal en cada pin (ensancha celdas si hace falta)"
cp "$OUT/cm05_stdcells.gds" "$TMP/antes.gds"
CELDAS=$(grep -oE "^\s*cell *\(\s*\w+" "$OUT/cm05_stdcells.lib" | sed 's/.*(//;s/ //g' | paste -sd, -)
python3 -I $S/legalize_pins.py "$OUT/cm05_stdcells.gds" "$OUT/cm05_stdcells.lef" "$CELDAS" | grep -v "^    "
python3 -I $S/lib_areas_from_lef.py "$OUT/cm05_stdcells.lef" "$OUT/cm05_stdcells.lib"
echo "== 6a. Bloqueo de vias de ruteo sobre celdas (cuadros OBS de M1 en puntos ilegales)"
python3 -I $S/add_via_block_obs.py "$OUT/cm05_stdcells.gds" "$OUT/cm05_stdcells.lef" "$CELDAS"
if [ -n "${DECK:-}" ]; then
    echo "== 6b. Verificacion por celda (deck: $DECK)"
    $S/verify_cells.sh "$OUT/cm05_stdcells.gds" "$TMP/antes.gds" "$DECK" ${CELDAS//,/ }
    echo "== 6c. Abutamiento: todas las celdas pegadas (N, espejo, alternado, filas FS)"
    python3 -I $S/abut_test.py "$OUT/cm05_stdcells.gds" "$OUT/cm05_stdcells.lef" "$CELDAS,FILL" "$TMP/abut.gds"
    $S/cm05_drc.sh "$TMP/abut.gds" ABUT "$DECK"
fi

# NOTA: no se agregan obstrucciones grandes en la capa via del LEF: qrouter las
# ignora y magic las toma como contactos M1-M2, cortocircuitando los pines en LVS.
# La regla 8.5 del ruteo se corrige despues de rutear (fix_route_vias.py).

echo "== 7. Archivos de configuracion (cm05.sh, .par, .magicrc, setup, .prm) se versionan tal cual"
rm -rf "$TMP"
echo "listo: $OUT"
