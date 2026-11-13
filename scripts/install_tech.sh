#!/usr/bin/env bash
# Instala la tecnologia cm05 dentro de la instalacion de qflow.
# Uso: install_tech.sh [PREFIX]   (por omision /opt/cm05_eda)
set -euo pipefail
PREFIX=${1:-/opt/cm05_eda}
HERE=$(cd "$(dirname "$0")/.." && pwd)
DEST="$PREFIX/share/qflow/tech/cm05"
mkdir -p "$DEST"
cp "$HERE"/tech/cm05/* "$DEST"/
sed -i "s|TECHDIR|$DEST|" "$DEST/cm05.magicrc"
echo "tecnologia cm05 instalada en $DEST"
