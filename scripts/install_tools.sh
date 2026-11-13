#!/usr/bin/env bash
# Instala las herramientas del flujo CM05_QFLOW en Ubuntu (Colab, 22.04 o 24.04).
#
#   apt : iverilog, magic, qrouter, yosys, netgen-lvs, tcsh (+ bibliotecas de graywolf)
#   pip : klayout (visualizar GDS) y matplotlib (formas de onda)
#   KLayout ejecutable (para el DRC oficial de CIDESI_CM05): paquete .deb
#         oficial si se puede descargar, si no el de apt
#   graywolf + qflow: binarios precompilados del release del repositorio para
#         esta version de Ubuntu; si no existen, se compilan desde GitHub
#   tecnologia cm05 dentro de qflow (install_tech.sh)
#
# Uso: [PREFIX=/opt/cm05_eda] install_tools.sh
set -euo pipefail
PREFIX=${PREFIX:-/opt/cm05_eda}
# qflow detecta graywolf/qrouter/etc. en el PATH al configurarse
export PATH="$PREFIX/bin:$PREFIX/shims:$PATH"
REPO=${CM05_REPO:-RodSchz/CM05_QFLOW}
TOOLS_TAG=${TOOLS_TAG:-tools-v1}
KLAYOUT_VER=${KLAYOUT_VER:-0.30.13}
HERE=$(cd "$(dirname "$0")" && pwd)
. /etc/os-release
UBU=${VERSION_ID}                       # 22.04, 24.04, ...
SUDO=""; [ "$(id -u)" = 0 ] || SUDO=sudo
export DEBIAN_FRONTEND=noninteractive

echo "== apt (Ubuntu $UBU)"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq iverilog magic qrouter yosys netgen-lvs tcsh curl \
    libgsl-dev tcl-dev tk-dev build-essential cmake git python3-pip > /dev/null

echo "== pip: klayout, matplotlib"
pip install -q klayout 2>/dev/null || pip install -q --break-system-packages klayout
# matplotlib ya viene en Colab. Si falta: pip normal (Ubuntu 22.04; la version de apt es muy vieja
# para Jupyter), luego apt (24.04, donde pip no instala en el sistema) y al final pip forzado
python3 -c "import matplotlib" 2>/dev/null || pip install -q matplotlib 2>/dev/null \
    || $SUDO apt-get install -y -qq python3-matplotlib > /dev/null \
    || pip install -q --break-system-packages matplotlib

echo "== KLayout ejecutable (DRC)"
# El deck de CIDESI_CM05 necesita KLayout >= 0.28; apt en Ubuntu 22.04 trae 0.26.
kl_ver() { QT_QPA_PLATFORM=offscreen klayout -v 2>/dev/null | awk '{print $2}'; }
kl_ok() { command -v klayout > /dev/null && [ "$(printf '%s\n0.28\n' "$(kl_ver)" | sort -V | head -1)" = 0.28 ]; }
if ! kl_ok; then
    DEB="klayout_${KLAYOUT_VER}-1_amd64.deb"
    # klayout.org; si falla, copia de respaldo en el release del repositorio; si no, apt
    if curl -fsL --retry 3 --retry-delay 5 -o "/tmp/$DEB" "https://www.klayout.org/downloads/Ubuntu-${UBU%%.*}/$DEB" \
       || curl -fsL --retry 3 -o "/tmp/$DEB" \
            "https://github.com/$REPO/releases/download/$TOOLS_TAG/klayout_${KLAYOUT_VER}-ubuntu${UBU%%.*}_amd64.deb"; then
        $SUDO apt-get install -y -qq "/tmp/$DEB" > /dev/null
    else
        $SUDO apt-get install -y -qq klayout > /dev/null
    fi
fi
echo "   KLayout $(kl_ver)"
kl_ok || echo "   AVISO: KLayout < 0.28; el DRC de CIDESI_CM05 no correra (descarga el .deb de klayout.org)"

echo "== graywolf + qflow"
$SUDO mkdir -p "$PREFIX/shims"
TGZ="cm05_eda-ubuntu${UBU}.tar.gz"
URL="https://github.com/$REPO/releases/download/$TOOLS_TAG/$TGZ"
if [ "$PREFIX" = /opt/cm05_eda ] && curl -fsL -o "/tmp/$TGZ" "$URL"; then
    echo "   binarios precompilados: $URL"
    $SUDO tar -xzf "/tmp/$TGZ" -C /
else
    echo "   sin binarios para Ubuntu $UBU: compilando desde GitHub (~2 min)"
    SRC=$(mktemp -d); LOG=/tmp/cm05_build.log; : > $LOG
    trap 'echo "ERROR compilando; ultimas lineas de $LOG:"; tail -20 $LOG' ERR
    git clone -q --depth 1 https://github.com/rubund/graywolf.git "$SRC/graywolf"
    git clone -q --depth 1 https://github.com/RTimothyEdwards/qflow.git "$SRC/qflow"
    cmake -S "$SRC/graywolf" -B "$SRC/graywolf/build" -DCMAKE_INSTALL_PREFIX="$PREFIX" >> $LOG 2>&1
    make -C "$SRC/graywolf/build" -j"$(nproc)" >> $LOG 2>&1
    $SUDO make -C "$SRC/graywolf/build" install >> $LOG 2>&1
    $SUDO ln -sf /usr/bin/netgen-lvs "$PREFIX/shims/netgen"
    (cd "$SRC/qflow" && ./configure --prefix="$PREFIX" --with-netgen="$PREFIX/shims/netgen" >> $LOG 2>&1 \
        && make -j"$(nproc)" >> $LOG 2>&1 && $SUDO make install >> $LOG 2>&1)
    trap - ERR
fi
# qflow busca "netgen"; Ubuntu lo instala como "netgen-lvs"
$SUDO ln -sf /usr/bin/netgen-lvs "$PREFIX/shims/netgen"

echo "== tecnologia cm05"
$SUDO "$HERE/install_tech.sh" "$PREFIX"

echo "Listo. Agrega al PATH: $PREFIX/bin:$PREFIX/shims"
