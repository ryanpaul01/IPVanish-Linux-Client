#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ipvanish-app"
ARCH="x86_64"
ROOT_DIR="$(pwd)"
APPDIR="${ROOT_DIR}/${APP_NAME}.AppDir"
OUT_NAME="${APP_NAME}-${ARCH}.AppImage"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${ROOT_DIR}/venv"

cleanup() {
    true
}
trap cleanup EXIT

if ! command -v wget >/dev/null 2>&1; then
    echo "wget is required"
    exit 1
fi

if ! command -v patchelf >/dev/null 2>&1; then
    echo "patchelf is required"
    exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "${PYTHON_BIN} not found"
    exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
pip3 install --upgrade pip
pip3 install -r requirements.txt

rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${APPDIR}/usr/lib"

cp ipvanish-app.py "${APPDIR}/usr/bin/${APP_NAME}.py"

cat > "${APPDIR}/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=IPVanish App
Exec=${APP_NAME}
Icon=${APP_NAME}
Categories=Network;Security;
Terminal=false
EOF

cat > "${APPDIR}/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export APPDIR="$HERE"
export HOME="${HOME}"
export PYWEBVIEW_GUI=qt
export QTWEBENGINE_DISABLE_SANDBOX=1
export PYTHONUNBUFFERED=1
exec "$HERE/venv/bin/python3" "$HERE/usr/bin/ipvanish-app.py" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

cat > "${APPDIR}/${APP_NAME}.png" <<'EOF'
EOF

if [ -f "${ROOT_DIR}/icon.png" ]; then
    cp "${ROOT_DIR}/icon.png" "${APPDIR}/${APP_NAME}.png"
elif [ -f "${ROOT_DIR}/ipvanish-app.png" ]; then
    cp "${ROOT_DIR}/ipvanish-app.png" "${APPDIR}/${APP_NAME}.png"
fi

ln -sf "${APP_NAME}.png" "${APPDIR}/.DirIcon"

cp -r "${VENV_DIR}" "${APPDIR}/venv"

APPIMAGE_TOOL="${ROOT_DIR}/appimagetool-x86_64.AppImage"
if [ ! -f "${APPIMAGE_TOOL}" ]; then
    wget -O "${APPIMAGE_TOOL}" https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "${APPIMAGE_TOOL}"
fi

ARCH=x86_64 "${APPIMAGE_TOOL}" "${APPDIR}" "${OUT_NAME}"
echo "Built: ${OUT_NAME}"
