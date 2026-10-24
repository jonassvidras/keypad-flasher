"""Verified Windows ISP tool download and read-only USB diagnostics."""

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path


TOOL_URL = "https://github.com/ch32-rs/wchisp/releases/download/nightly/wchisp-win-x64.zip"
TOOL_ARCHIVE_SHA256 = "edd01f0ee4e7e665f65baf30a0a9aae4e6024b2665f1725731295a3e6d8190ca"
TOOL_EXE_SHA256 = "bd47ff8ace733630864550f4a925676b485dac9d998a91dc7154105a1d2b2765"
TOOL_ENTRY = "wchisp-win-x64/wchisp.exe"
MAX_ARCHIVE_BYTES = 2_000_000
MAX_EXE_BYTES = 3_000_000


def managed_tool_path():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise ValueError("LOCALAPPDATA is unavailable; cannot install the Windows ISP tool")
    return Path(base) / "KeypadOpen" / "tools" / "wchisp.exe"


def checked_tool(path):
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return False
    return digest == TOOL_EXE_SHA256


def tool_from_archive(data):
    if hashlib.sha256(data).hexdigest() != TOOL_ARCHIVE_SHA256:
        raise ValueError("The official wchisp archive checksum changed; download rejected")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entry = archive.getinfo(TOOL_ENTRY)
            if entry.file_size > MAX_EXE_BYTES:
                raise ValueError("wchisp executable exceeds the expected size")
            executable = archive.read(entry)
    except (KeyError, zipfile.BadZipFile) as error:
        raise ValueError("The wchisp archive has an unexpected format") from error
    if hashlib.sha256(executable).hexdigest() != TOOL_EXE_SHA256:
        raise ValueError("The wchisp executable checksum changed; download rejected")
    return executable


def install_tool(path):
    if sys.platform != "win32":
        raise ValueError("Automatic wchisp setup is only available on Windows")
    request = urllib.request.Request(TOOL_URL, headers={"User-Agent": "KeypadOpen-Installer"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            archive = response.read(MAX_ARCHIVE_BYTES + 1)
    except OSError as error:
        raise ValueError(f"Could not download wchisp from GitHub: {error}") from error
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("The wchisp download exceeds the expected size")
    executable = tool_from_archive(archive)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix="wchisp-", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(executable)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return TOOL_EXE_SHA256


def windows_usb_devices(wait_seconds=20):
    if sys.platform != "win32":
        raise ValueError("Windows USB diagnostics are only available on Windows")
    script = (
        "Get-PnpDevice -PresentOnly | "
        "Where-Object { $_.InstanceId -like 'USB\\VID_4348&PID_55E0*' } | "
        "Select-Object InstanceId,Status,Class,FriendlyName | ConvertTo-Json -Compress"
    )
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, errors="replace", timeout=10, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError(f"Windows USB check failed: {error}") from error
        if result.returncode:
            raise ValueError(f"Windows USB check failed: {result.stderr.strip()[-1000:]}")
        try:
            parsed = json.loads(result.stdout) if result.stdout.strip() else []
        except ValueError as error:
            raise ValueError("Windows returned an unreadable USB device list") from error
        devices = parsed if isinstance(parsed, list) else [parsed]
        if devices or time.monotonic() >= deadline:
            return [{"instanceId": item.get("InstanceId"), "status": item.get("Status"),
                     "name": item.get("FriendlyName") or "WCH USB ISP device"} for item in devices]
        time.sleep(0.5)
