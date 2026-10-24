"""Read-only checks for a CH552 firmware image and optional USB ISP device."""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path


APPLICATION_LIMIT = 0x3800
CHIP_PATTERN = re.compile(r"Chip:\s*CH552\[0x5211\]", re.IGNORECASE)
BOOTLOADER_PATTERN = re.compile(r"BTVER\(bootloader ver\):\s*([0-9.]+)")


def inspect_hex(path):
    try:
        contents = path.read_bytes()
    except OSError as error:
        raise ValueError(f"Cannot read HEX file: {error}") from error

    memory = {}
    upper_address = 0
    end_seen = False
    lines = contents.decode("ascii").splitlines()
    if not lines:
        raise ValueError("HEX file is empty")

    for line_number, line in enumerate(lines, 1):
        if end_seen:
            raise ValueError(f"Line {line_number}: data follows the end-of-file record")
        if not line.startswith(":"):
            raise ValueError(f"Line {line_number}: expected an Intel HEX record")
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as error:
            raise ValueError(f"Line {line_number}: invalid hex digits") from error
        if len(record) < 5 or len(record) != record[0] + 5:
            raise ValueError(f"Line {line_number}: invalid record length")
        if sum(record) & 0xFF:
            raise ValueError(f"Line {line_number}: invalid checksum")

        count = record[0]
        offset = (record[1] << 8) | record[2]
        kind = record[3]
        data = record[4:-1]
        if kind == 0:
            for index, value in enumerate(data):
                address = upper_address + offset + index
                if address >= APPLICATION_LIMIT:
                    raise ValueError(
                        f"Line {line_number}: address 0x{address:04X} reaches the bootloader region"
                    )
                if address in memory:
                    raise ValueError(f"Line {line_number}: overlapping address 0x{address:04X}")
                memory[address] = value
        elif kind == 1:
            if count or offset:
                raise ValueError(f"Line {line_number}: malformed end-of-file record")
            end_seen = True
        elif kind in (2, 4):
            if count != 2 or offset:
                raise ValueError(f"Line {line_number}: malformed extended-address record")
            extension = int.from_bytes(data, "big")
            upper_address = extension << (4 if kind == 2 else 16)
        else:
            raise ValueError(f"Line {line_number}: unsupported record type {kind}")

    if not end_seen:
        raise ValueError("HEX file has no end-of-file record")
    if not memory or 0 not in memory:
        raise ValueError("HEX file has no application entry at address 0x0000")
    return {
        "bytes": len(memory),
        "last_address": max(memory),
        "sha256": hashlib.sha256(contents).hexdigest(),
    }


def probe_bootloader(executable):
    if not executable.is_file():
        if str(executable).startswith("'") and str(executable).endswith("'"):
            raise ValueError(
                "wchisp path includes literal single quotes; in Command Prompt use double quotes instead"
            )
        raise ValueError(f"wchisp executable not found: {executable}")
    try:
        result = subprocess.run(
            [str(executable), "info"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Could not run wchisp info: {error}") from error
    output = result.stdout + result.stderr
    if result.returncode or not CHIP_PATTERN.search(output):
        raise ValueError(f"wchisp info did not identify a CH552[0x5211]:\n{output.strip()}")
    bootloader = BOOTLOADER_PATTERN.search(output)
    return bootloader.group(1) if bootloader else "not reported"


def main():
    parser = argparse.ArgumentParser(
        description="Validate a CH552 Intel HEX image; optionally run only 'wchisp info'."
    )
    parser.add_argument(
        "hex_file",
        nargs="?",
        type=Path,
        default=Path(__file__).parent / "build" / "KeypadOpen.ino.hex",
    )
    parser.add_argument("--probe", metavar="WCHISP_EXE", type=Path)
    args = parser.parse_args()

    try:
        result = inspect_hex(args.hex_file)
        print(f"HEX: {args.hex_file}")
        print(f"Image SHA-256: {result['sha256']}")
        print(f"Programmed bytes: {result['bytes']}; last address: 0x{result['last_address']:04X}")
        print(f"Application limit: 0x{APPLICATION_LIMIT:04X} (exclusive) - PASS")
        if args.probe:
            version = probe_bootloader(args.probe)
            print(f"Read-only USB ISP check: CH552[0x5211], bootloader {version} - PASS")
        else:
            print("USB ISP check: NOT RUN (pass --probe with the path to wchisp.exe)")
        print("No device write, erase, upload, or configuration command was run.")
    except (UnicodeError, ValueError) as error:
        print(f"Preflight FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
