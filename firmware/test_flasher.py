"""Offline safety tests; no USB device is accessed."""

import hashlib
import io
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from dataclasses import replace
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flasher
import flasher_support


INFO = "Chip: CH552[0x5211]\nChip UID: 11-22-33-44-00-00-00-00\nBTVER(bootloader ver): 02.50"


class FlasherTests(unittest.TestCase):
    def test_known_image(self):
        image = flasher.checked_image()
        self.assertEqual(image["sha256"], flasher.V2_IMAGE.sha256)
        self.assertEqual(image["bytes"], 11905)
        self.assertEqual(image["last_address"], 0x2ED0)

    def test_v1_recovery_image_is_separate_and_pinned(self):
        image = flasher.checked_image(flasher.V1_IMAGE)
        self.assertEqual(image["sha256"], flasher.V1_IMAGE.sha256)
        self.assertEqual(image["bytes"], 9666)
        self.assertNotEqual(flasher.V2_IMAGE.path, flasher.V1_IMAGE.path)
        with self.assertRaisesRegex(ValueError, "differs from the pinned build"):
            flasher.checked_image(replace(flasher.V1_IMAGE, sha256="0" * 64))

    def test_probe_rejects_wrong_bootloader(self):
        with patch.object(flasher, "run_wchisp", return_value=INFO.replace("02.50", "02.40")):
            with self.assertRaisesRegex(ValueError, "Expected CH552"):
                flasher.probe(Path("wchisp"))

    def test_unverified_wchisp_is_never_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "wchisp.exe"
            executable.write_bytes(b"unverified")
            with patch.object(flasher.subprocess, "run") as process:
                with self.assertRaisesRegex(ValueError, "differs from the tested SHA-256"):
                    flasher.run_wchisp(executable, "info")
                process.assert_not_called()

    def test_flash_rechecks_uid_before_write(self):
        with patch.object(flasher, "run_wchisp", return_value=INFO) as run:
            with self.assertRaisesRegex(ValueError, "changed"):
                flasher.flash(Path("wchisp"), "00-00")
            run.assert_called_once_with(Path("wchisp"), "info")

    def test_flash_requires_verification_message(self):
        with patch.object(flasher, "run_wchisp", side_effect=[INFO, INFO]) as run:
            with self.assertRaisesRegex(ValueError, "without a confirmed verify"):
                flasher.flash(Path("wchisp"), "11-22-33-44-00-00-00-00")
            self.assertEqual(run.call_args_list[1].args[1:3], ("flash", "--no-reset"))

    def test_tool_download_rejects_changed_archive_and_executable(self):
        executable = b"tested wchisp fixture"
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            archive.writestr(flasher_support.TOOL_ENTRY, executable)
        payload = archive_bytes.getvalue()
        with self.assertRaisesRegex(ValueError, "archive checksum changed"):
            flasher_support.tool_from_archive(payload)
        with patch.object(flasher_support, "TOOL_ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest()):
            with self.assertRaisesRegex(ValueError, "executable checksum changed"):
                flasher_support.tool_from_archive(payload)
            with patch.object(flasher_support, "TOOL_EXE_SHA256", hashlib.sha256(executable).hexdigest()):
                self.assertEqual(flasher_support.tool_from_archive(payload), executable)

    def test_tool_download_is_opt_in_and_writes_only_after_checks(self):
        executable = b"tested wchisp fixture"
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            archive.writestr(flasher_support.TOOL_ENTRY, executable)
        payload = archive_bytes.getvalue()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "tools" / "wchisp.exe"
            with patch.object(flasher_support, "TOOL_ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest()), \
                    patch.object(flasher_support, "TOOL_EXE_SHA256", hashlib.sha256(executable).hexdigest()), \
                    patch.object(flasher_support.urllib.request, "urlopen", return_value=io.BytesIO(payload)):
                self.assertEqual(flasher_support.install_tool(destination), hashlib.sha256(executable).hexdigest())
            self.assertEqual(destination.read_bytes(), executable)

    def test_windows_usb_diagnostic_reports_status_without_changes(self):
        output = json.dumps({"InstanceId": "USB\\VID_4348&PID_55E0\\TEST",
                             "Status": "Error", "FriendlyName": None})
        result = unittest.mock.Mock(returncode=0, stdout=output, stderr="")
        with patch.object(flasher_support.subprocess, "run", return_value=result) as process:
            devices = flasher_support.windows_usb_devices(wait_seconds=0)
        self.assertEqual(devices[0]["status"], "Error")
        self.assertIn("Get-PnpDevice -PresentOnly", process.call_args.args[0][-1])

    def test_loopback_api_rejects_cross_origin_write(self):
        server = flasher.Installer(Path("wchisp"), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection("127.0.0.1", server.server_port)
            connection.request("POST", "/api/probe", body="{}", headers={
                "Origin": "https://example.com", "Content-Type": "application/json",
                "X-Installer-Token": server.token,
            })
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            connection.close()

            connection = HTTPConnection("127.0.0.1", server.server_port)
            connection.request("POST", "/api/flash", body=json.dumps({
                "uid": "11-22-33-44-00-00-00-00", "confirmation": "REPLACE STOCK FIRMWARE",
            }), headers={"Origin": f"http://127.0.0.1:{server.server_port}",
                        "Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_local_api_requires_probe_and_exact_confirmation(self):
        server = flasher.Installer(Path("wchisp"), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        uid = "11-22-33-44-00-00-00-00"

        def post(path, body):
            connection = HTTPConnection("127.0.0.1", server.server_port)
            connection.request("POST", path, body=json.dumps(body), headers={
                "Origin": origin, "Content-Type": "application/json",
                "X-Installer-Token": server.token,
            })
            response = connection.getresponse()
            result = response.status, json.loads(response.read())
            connection.close()
            return result

        try:
            with patch.object(flasher, "probe", return_value=(uid, INFO)), \
                    patch.object(flasher, "flash", return_value=INFO + "\nVerify OK") as write:
                approved = {"uid": uid, "confirmation": "REPLACE STOCK FIRMWARE",
                            "boardChecks": ["chip", "r12", "layout"], "stockLossAcknowledged": True}
                self.assertEqual(post("/api/flash", approved)[0], 400)
                self.assertEqual(post("/api/probe", {})[0], 200)
                self.assertEqual(post("/api/flash", {"uid": uid,
                    "confirmation": "replace stock firmware"})[0], 400)
                self.assertEqual(post("/api/flash", {**approved, "boardChecks": []})[0], 400)
                self.assertEqual(post("/api/flash", approved)[0], 200)
                write.assert_called_once_with(server.executable, uid, flasher.V2_IMAGE)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_v1_recovery_api_uses_only_v1_image(self):
        server = flasher.Installer(Path("wchisp"), 0, image_spec=flasher.V1_IMAGE)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        uid = "11-22-33-44-00-00-00-00"

        def post(path, body):
            connection = HTTPConnection("127.0.0.1", server.server_port)
            connection.request("POST", path, body=json.dumps(body), headers={
                "Origin": origin, "Content-Type": "application/json",
                "X-Installer-Token": server.token,
            })
            response = connection.getresponse()
            result = response.status, json.loads(response.read())
            connection.close()
            return result

        try:
            connection = HTTPConnection("127.0.0.1", server.server_port)
            connection.request("GET", "/api/status", headers={"Host": f"127.0.0.1:{server.server_port}"})
            response = connection.getresponse()
            status = json.loads(response.read())
            connection.close()
            self.assertEqual(status["imageKind"], "tested-v1")
            self.assertEqual(status["sha256"], flasher.V1_IMAGE.sha256)
            with patch.object(flasher, "probe", return_value=(uid, INFO)), \
                    patch.object(flasher, "flash", return_value=INFO + "\nVerify OK") as write:
                approved = {"uid": uid, "confirmation": "REPLACE STOCK FIRMWARE",
                            "boardChecks": ["chip", "r12", "layout"],
                            "stockLossAcknowledged": True}
                self.assertEqual(post("/api/probe", {})[0], 200)
                self.assertEqual(post("/api/flash", {**approved, "confirmation": "WRONG CONFIRMATION"})[0], 400)
                write.assert_not_called()
                self.assertEqual(post("/api/flash", approved)[0], 200)
                write.assert_called_once_with(server.executable, uid, flasher.V1_IMAGE)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
