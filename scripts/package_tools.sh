#!/usr/bin/env bash
# Compila graywolf y qflow en /opt/cm05_eda y los empaqueta para publicarlos
# como release (lo usa .github/workflows/tools.yml en cada version de Ubuntu).
# Uso: package_tools.sh <salida.tar.gz>
set -euo pipefail
OUT=$(realpath -m "$1")
PREFIX=/opt/cm05_eda
# qflow detecta graywolf/qrouter/etc. en el PATH al configurarse
export PATH="$PREFIX/bin:$PREFIX/shims:$PATH"
SUDO=""; [ "$(id -u)" = 0 ] || SUDO=sudo
SRC=$(mktemp -d)
git clone -q --depth 1 https://github.com/rubund/graywolf.git "$SRC/graywolf"
git clone -q --depth 1 https://github.com/RTimothyEdwards/qflow.git "$SRC/qflow"
echo "graywolf $(git -C "$SRC/graywolf" rev-parse --short HEAD), qflow $(git -C "$SRC/qflow" rev-parse --short HEAD)"
cmake -S "$SRC/graywolf" -B "$SRC/graywolf/build" -DCMAKE_INSTALL_PREFIX="$PREFIX"
make -C "$SRC/graywolf/build" -j"$(nproc)"
$SUDO make -C "$SRC/graywolf/build" install
$SUDO mkdir -p "$PREFIX/shims"
$SUDO ln -sf /usr/bin/netgen-lvs "$PREFIX/shims/netgen"
(cd "$SRC/qflow" && ./configure --prefix="$PREFIX" --with-netgen="$PREFIX/shims/netgen" && make -j"$(nproc)" && $SUDO make install)
tar -czf "$OUT" -C / opt/cm05_eda/bin opt/cm05_eda/share opt/cm05_eda/shims $( [ -d $PREFIX/lib ] && echo opt/cm05_eda/lib )
ls -l "$OUT"
