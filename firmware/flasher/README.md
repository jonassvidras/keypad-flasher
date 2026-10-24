# KeypadOpen local flasher

The default local installer is pinned to the owner-tested KeypadOpen v2 image.
It runs a loopback-only browser UI backed by `wchisp`; it is **not** a WebUSB
flasher. The earlier v1 image is available through `--v1` for source-based
recovery. Neither can restore the factory program.

The source-only `--usb-name-candidate` option is for the owner's local
[USB-name test](../USB_NAME_TEST.md). It accepts only the pinned candidate
from `firmware/build/usb-names/`; the Windows package does not include it.

## Windows 11 beta

Build a distributable folder from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\firmware\build_windows_installer.ps1
```

The package contains only v2 and the local UI. `wchisp.exe` is not bundled;
the user must opt into a download that verifies both its archive and binary
hashes. The upstream nightly URL may move and fail closed. The installer does
not change USB drivers. See [the included package guide](WINDOWS_PACKAGE.md).

To run from source, use a previously verified `wchisp` executable:

```powershell
python .\firmware\flasher.py --wchisp C:\path\to\wchisp.exe
```

The UI requires a board-match checklist, a read-only CH552/bootloader probe,
the exact typed confirmation, and an acknowledgment that stock firmware may
be lost. It rechecks chip UID immediately before calling `wchisp flash
--no-reset` with erase and verify enabled. If verification fails, stop rather
than blindly retrying. The matching PCB's empty R12 pads provide the observed
USB ISP entry path, but compatibility with other board revisions is unproven.

## macOS

Only the [read-only browser probe](../MACOS_TEST.md) is ready for owner testing.
`run_macos_installer.sh` is source-only and has not passed a Mac hardware flash
test; no Mac flashing package should be published yet. It requires a separately
obtained executable `wchisp` and a deliberate, supervised run.
