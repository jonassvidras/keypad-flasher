"""Loopback-only browser front end for pinned KeypadOpen images and wchisp."""

import argparse
import json
import re
import secrets
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from flasher_support import checked_tool, install_tool, managed_tool_path, windows_usb_devices
from preflight import inspect_hex


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "flasher"
@dataclass(frozen=True)
class ImageSpec:
    path: Path
    sha256: str
    bytes: int
    last_address: int
    kind: str
    confirmation: str


V2_IMAGE = ImageSpec(
    ROOT / "release" / "KeypadOpen-v2.hex",
    "631c148775cec49ad15d1b5c2ae9d164493c9ff42332eb0aa6210d0e39fd8da5",
    11905, 0x2ED0, "owner-tested-v2", "REPLACE STOCK FIRMWARE",
)
V1_IMAGE = ImageSpec(
    ROOT / "release" / "KeypadOpen-v1.hex",
    "c4c2c0c185a3ac0ac13c79c9aa6236a05014c9c1cc39d96c55dfe328efebe5b5",
    9666, 0x260F, "tested-v1", "REPLACE STOCK FIRMWARE",
)
CHIP = re.compile(r"Chip:\s*CH552\[0x5211\]", re.IGNORECASE)
VERSION = re.compile(r"BTVER\(bootloader ver\):\s*02\.50", re.IGNORECASE)
UID = re.compile(r"Chip UID:\s*([0-9A-F-]+)", re.IGNORECASE)


def checked_image(spec=V2_IMAGE):
    image = inspect_hex(spec.path)
    if (image["sha256"] != spec.sha256 or image["bytes"] != spec.bytes
            or image["last_address"] != spec.last_address):
        raise ValueError("Firmware image differs from the pinned build; flashing is disabled")
    return image


def run_wchisp(executable, *arguments, timeout=30):
    if sys.platform == "win32" and not checked_tool(executable):
        raise ValueError("wchisp.exe is missing or differs from the tested SHA-256; flashing is disabled")
    result = subprocess.run(
        [str(executable), "-u", *arguments], capture_output=True, text=True,
        errors="replace", timeout=timeout, check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise ValueError(f"wchisp failed (exit {result.returncode}):\n{output[-5000:]}")
    return output


def probe(executable, spec=V2_IMAGE):
    checked_image(spec)
    output = run_wchisp(executable, "info")
    if not CHIP.search(output) or not VERSION.search(output):
        raise ValueError("Expected CH552[0x5211] with USB bootloader 02.50; do not flash this device")
    uid = UID.search(output)
    if not uid:
        raise ValueError("wchisp did not report a chip UID; flashing is disabled")
    return uid.group(1).upper(), output


def flash(executable, acknowledged_uid, spec=V2_IMAGE):
    checked_image(spec)
    uid, _ = probe(executable, spec)
    if uid != acknowledged_uid:
        raise ValueError("The connected chip changed since the confirmation; flashing is disabled")
    output = run_wchisp(executable, "flash", "--no-reset", str(spec.path), timeout=120)
    if not CHIP.search(output) or "Verify OK" not in output:
        raise ValueError(f"Flash command exited without a confirmed verify. Do not reconnect yet:\n{output[-5000:]}")
    return output


class Installer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, executable, port, managed_tool=None, image_spec=V2_IMAGE):
        super().__init__(("127.0.0.1", port), Handler)
        self.executable = executable
        self.managed_tool = managed_tool
        self.image_spec = image_spec
        self.token = secrets.token_urlsafe(32)
        self.uid = None
        self.busy = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _local_request(self):
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        address = f"http://127.0.0.1:{self.server.server_port}"
        return host == f"127.0.0.1:{self.server.server_port}" and (
            origin is None or origin == address
        )

    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, value):
        self._send(code, json.dumps(value).encode("utf-8"))

    def do_GET(self):
        if not self._local_request():
            return self._json(403, {"error": "Localhost only"})
        path = urlsplit(self.path).path
        if path == "/api/status":
            try:
                image = checked_image(self.server.image_spec)
            except ValueError as error:
                return self._json(500, {"error": str(error)})
            backend_ready = (checked_tool(self.server.executable) if sys.platform == "win32"
                             else self.server.executable.is_file())
            return self._json(200, {"token": self.server.token, "sha256": image["sha256"],
                                    "bytes": image["bytes"], "lastAddress": image["last_address"],
                                    "imageKind": self.server.image_spec.kind,
                                    "confirmation": self.server.image_spec.confirmation,
                                    "platform": sys.platform,
                                    "toolSetupAvailable": self.server.managed_tool is not None,
                                    "backendReady": backend_ready,
                                    "backendError": ("wchisp.exe has an unrecognized checksum" if
                                                     self.server.executable.is_file() and not backend_ready else None)})
        files = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
                 "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path == "/board.svg":
            return self._send(200, (WEB / "board.svg").read_bytes(), "image/svg+xml")
        if path not in files:
            return self._json(404, {"error": "Not found"})
        filename, mime = files[path]
        self._send(200, (WEB / filename).read_bytes(), mime)

    def do_POST(self):
        if not self._local_request() or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}":
            return self._json(403, {"error": "Wrong origin"})
        if self.headers.get("X-Installer-Token") != self.server.token:
            return self._json(403, {"error": "Invalid session token"})
        if self.headers.get("Content-Type") != "application/json":
            return self._json(415, {"error": "Expected JSON"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json(400, {"error": "Invalid request length"})
        if length > 2048 or length < 0:
            return self._json(413, {"error": "Request too large"})
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Invalid request")
        except (UnicodeError, ValueError):
            return self._json(400, {"error": "Invalid JSON"})
        if not self.server.busy.acquire(blocking=False):
            return self._json(409, {"error": "Another device operation is running"})
        try:
            if self.path == "/api/probe":
                uid, output = probe(self.server.executable, self.server.image_spec)
                self.server.uid = uid
                return self._json(200, {"uid": uid, "log": output})
            if self.path == "/api/install-tool":
                if not self.server.managed_tool:
                    return self._json(400, {"error": "Tool download is unavailable on this platform"})
                digest = install_tool(self.server.managed_tool)
                self.server.executable = self.server.managed_tool
                return self._json(200, {"sha256": digest})
            if self.path == "/api/windows-usb":
                return self._json(200, {"devices": windows_usb_devices()})
            if self.path == "/api/flash":
                if (payload.get("confirmation") != self.server.image_spec.confirmation
                        or payload.get("boardChecks") != ["chip", "r12", "layout"]
                        or payload.get("stockLossAcknowledged") is not True
                        or payload.get("uid") != self.server.uid or not self.server.uid):
                    return self._json(400, {"error": "Device confirmation is required"})
                uid = self.server.uid
                self.server.uid = None
                return self._json(200, {"log": flash(self.server.executable, uid, self.server.image_spec)})
            return self._json(404, {"error": "Not found"})
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            return self._json(400, {"error": str(error)})
        finally:
            self.server.busy.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wchisp", type=Path, help="Path to the tested wchisp executable")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--v1", action="store_true", help="Use the earlier v1 image for recovery")
    args = parser.parse_args()
    image_spec = V1_IMAGE if args.v1 else V2_IMAGE
    executable_folder = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    managed = managed_tool_path() if sys.platform == "win32" else None
    if args.wchisp:
        executable = args.wchisp
    elif managed:
        local = executable_folder / "wchisp.exe"
        executable = local if local.is_file() else managed
    else:
        executable = executable_folder / "wchisp"
    checked_image(image_spec)
    server = Installer(executable.resolve(), args.port, managed, image_spec)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"KeypadOpen installer: {url}")
    print(f"Only the pinned {image_spec.kind} image is available. Press Ctrl+C to stop.")
    if sys.platform == "win32" and not checked_tool(executable):
        print("A verified wchisp.exe is not installed; the page can download it only on request.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
