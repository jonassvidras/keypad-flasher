#!/bin/sh
set -eu

if [ "$(uname -s)" != Darwin ]; then
  echo "This launcher is for macOS." >&2
  exit 1
fi
if [ "$#" -ne 1 ] || [ ! -x "$1" ]; then
  echo "Usage: ./firmware/run_macos_installer.sh /absolute/path/to/wchisp" >&2
  echo "The macOS flashing path has not yet passed a hardware test." >&2
  exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$script_dir/preflight.py" "$script_dir/release/KeypadOpen-v2.hex"
exec python3 "$script_dir/flasher.py" --wchisp "$1"
