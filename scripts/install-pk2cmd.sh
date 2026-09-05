#!/usr/bin/env bash
# Installs pk2cmd (jaka-fi/pk2cmd, a maintained fork of Microchip's own
# tool driving PICkit2/PICkit3/PICkit3.5/PKOB clones) for platform-epic8's
# upload target. See docs/pk2cmd-LICENSE.md before running this: pk2cmd
# is Microchip's own licensed software, not MIT, fetched here unmodified.
#
# Downloads the exact release we've verified (checksum below), extracts
# the AppImage rather than running it directly (many environments lack
# FUSE), and installs the binary plus its device database to
# ~/.local/share/epic8/pk2cmd/. The builder always passes -B<path> to
# pk2cmd, so the install location does not need to be on PATH itself,
# only EPIC8_PK2CMD_PATH needs to point at the binary (or leave PATH to
# find it if you also symlink it yourself).

set -euo pipefail

PK2CMD_VERSION="v1.27.01"
PK2CMD_SHA256="11e96efef2e57eb946edf2c5daf622e96b5be20c6ebfb62066d296bfd681b1e9"
PK2CMD_URL="https://github.com/jaka-fi/pk2cmd/releases/download/${PK2CMD_VERSION}/pk2cmd-x86_64.AppImage"
UDEV_URL="https://raw.githubusercontent.com/jaka-fi/pk2cmd/master/60-pickit.rules"

INSTALL_DIR="${EPIC8_PK2CMD_DIR:-$HOME/.local/share/epic8/pk2cmd}"

if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
    echo "This script only handles Linux x86_64 today." >&2
    echo "See https://github.com/jaka-fi/pk2cmd/releases/tag/${PK2CMD_VERSION} for other platforms." >&2
    exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading pk2cmd ${PK2CMD_VERSION}..."
curl -sL -o "$tmp/pk2cmd.AppImage" "$PK2CMD_URL"

echo "Verifying checksum..."
echo "${PK2CMD_SHA256}  $tmp/pk2cmd.AppImage" | sha256sum -c -

chmod +x "$tmp/pk2cmd.AppImage"
(cd "$tmp" && ./pk2cmd.AppImage --appimage-extract >/dev/null)

mkdir -p "$INSTALL_DIR"
cp "$tmp/squashfs-root/usr/bin/pk2cmd" "$INSTALL_DIR/pk2cmd"
cp "$tmp/squashfs-root/usr/bin/PK2DeviceFile.dat" "$INSTALL_DIR/PK2DeviceFile.dat"
chmod +x "$INSTALL_DIR/pk2cmd"

echo "Installed to $INSTALL_DIR"
echo
echo "Set this and 'pio run -t upload' will find it:"
echo "  export EPIC8_PK2CMD_PATH=$INSTALL_DIR/pk2cmd"
echo
echo "USB permissions: PICkit2/3/PKOB need a udev rule to be usable"
echo "without root. Install one with:"
echo "  curl -sL $UDEV_URL | sudo tee /etc/udev/rules.d/60-pickit.rules"
echo "  sudo udevadm control --reload-rules && sudo udevadm trigger"
echo "then unplug and replug the programmer."
echo
echo "PICkit3/PKOB clones without 'scripting firmware' cannot be driven"
echo "by pk2cmd on Linux at all (no firmware-update support here); that"
echo "one-time update needs the Windows GUI. See docs/getting-started.md."
echo
echo "pk2cmd is Microchip's own licensed software, not MIT. Read"
echo "docs/pk2cmd-LICENSE.md before distributing anything built on it."
