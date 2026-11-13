#!/usr/bin/env bash
# Flujo completo Verilog -> GDS para CIDESI_CM05 con qflow.
#   1. qflow: sintesis (yosys), colocacion (graywolf), ruteo 2 capas (qrouter),
#      migracion y LVS (magic + netgen)
#   2. GDS con celdas completas (cm05_gds.sh)
#   3. Legalizador post-ruteo: vias de ruteo lejos de bordes de poly/activo
#      (regla 8.5) y relleno de muescas (fix_route_vias.py)
#   4. Equivalencia de netlist antes/despues del legalizador (netcompare.py)
#   5. DRC con el deck oficial de CIDESI_CM05 en KLayout (cm05_drc.sh)
# Uso: [CM05_STRICT=1] cm05_flow.sh <modulo> <dir_proyecto> <drc.lydrc> [PREFIX]
# Configuracion opcional (variables de entorno):
#   CM05_DENSIDAD=0.5     densidad de colocacion fija (sin: automatica 0.7 -> 0.3)
#   CM05_ASPECTO=0.75     proporcion alto/ancho del chip (sin: la de la tecnologia)
#   CM05_PINES=pines.json posicion de pines por lado (ver make_cel2.py); si no se da
#                         y existe <dir>/<modulo>.cel2, qflow lo usa tal cual
# El proyecto debe tener source/<modulo>.v. Resultado: <modulo>_cm05.gds
set -euo pipefail
MOD=$1; DIR=$2; DECK=$3; PREFIX=${4:-/opt/cm05_eda}
S=$(cd "$(dirname "$0")" && pwd)
export PATH="$PREFIX/bin:$PREFIX/shims:$PATH"
cd "$DIR"
echo "== qflow: sintesis"
qflow synthesize -T cm05 "$MOD" > qflow.log 2>&1 || true
grep -A40 "Number of cells" log/synth.log | grep -E "^\s+[A-Z]+[A-Z0-9]*\s+[0-9]+" || true
# Proporcion del chip: en el .par del proyecto (qflow lo prefiere al de la tecnologia)
cp "$PREFIX/share/qflow/tech/cm05/cm05.par" "${MOD}.par"   # se reinicia en cada corrida
if [ -n "${CM05_ASPECTO:-}" ]; then
    sed -i "s/^TWMC\*chip.aspect.ratio.*/TWMC*chip.aspect.ratio : $CM05_ASPECTO/" "${MOD}.par"
    echo "   proporcion alto/ancho: $CM05_ASPECTO"
fi
# Posicion de pines
if [ -n "${CM05_PINES:-}" ]; then
    python3 -I "$S/make_cel2.py" "${MOD}.rtlnopwr.v" "$CM05_PINES" "${MOD}.cel2"
elif [ -f "${MOD}.cel2" ]; then
    echo "   posicion de pines: ${MOD}.cel2"
fi
# Con 2 metales el ruteo depende del espacio libre entre celdas: si falla se
# reintenta con menor densidad de colocacion. (No usar rowSep: graywolf/qflow
# enciman filas y el LVS falla.)
DENSIDADES="0.7 0.5 0.4 0.3"
[ -n "${CM05_DENSIDAD:-}" ] && DENSIDADES="$CM05_DENSIDAD"
ok=0
for DN in $DENSIDADES; do
    sed -i '/initial_density/d' project_vars.sh; echo "set initial_density = $DN" >> project_vars.sh
    qflow place -T cm05 "$MOD" >> qflow.log 2>&1 || true
    if [ -f "${MOD}.cel2" ]; then
        # con lados fijados graywolf amontona los pines: repartirlos sobre pistas
        python3 -I "$S/spread_pins.py" "${MOD}.def" $( [ -f "${MOD}_unroute.def" ] && echo "${MOD}_unroute.def" )
    fi
    qflow route -T cm05 "$MOD" >> qflow.log 2>&1 || true
    r=$(grep -E "Final: " log/route.log | tail -1)
    echo "   densidad=$DN -> $r"
    if echo "$r" | grep -q "No failed routes"; then ok=1; break; fi
done
if [ $ok = 0 ]; then
    echo "ERROR: el ruteo no se completo (ver log/route.log). Opciones: bajar la densidad"
    echo "       (o dejarla automatica), cambiar la proporcion del chip o liberar pines fijados."
    exit 1
fi
echo "== qflow: migracion y LVS"
qflow migrate lvs -T cm05 "$MOD" >> qflow.log 2>&1 || true
grep -hE "Circuits match|Total errors" qflow.log | tail -2
if ! grep -q "Circuits match uniquely" qflow.log; then
    echo "ERROR: LVS no coincide (ver comp.out)"; exit 1
fi
echo "== GDS"
"$S/cm05_gds.sh" "$MOD" . "$PREFIX" > /dev/null
echo "== Legalizador post-ruteo (regla 8.5)"
python3 -I "$S/fix_route_vias.py" "${MOD}.gds" "$MOD" "${MOD}_cm05.gds"
python3 -I "$S/netcompare.py" "${MOD}.gds" "${MOD}_cm05.gds" "$MOD" | tail -1
echo "== DRC CIDESI_CM05 (KLayout)"
"$S/cm05_drc.sh" "${MOD}_cm05.gds" "$MOD" "$DECK"
# Modo estricto (pruebas automaticas): falla si el DRC no queda en cero
if [ "${CM05_STRICT:-0}" = 1 ]; then
    n=$(python3 -I "$S/rdb_summary.py" "${MOD}_cm05_drc.lyrdb" | awk '/TOTAL/{print $2}')
    [ "$n" = 0 ] || { echo "ERROR: DRC con $n errores"; exit 2; }
fi
