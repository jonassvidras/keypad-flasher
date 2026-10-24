<h1 align="center">KeypadOpen</h1>

<p align="center">Your three-key keypad, opened up.<br>Custom firmware, a guided local flasher, and more ways to use the keys, knob, and lights.</p>

**Beta:** KeypadOpen v2 has been tested on one matching CH552G board, not on every keypad sold under the same listing. Flashing erases the factory program, and we do not have a restorable factory firmware image. Read the [board reference](docs/HARDWARE.md) before continuing.

## Windows 11

1. Compare your PCB with the [board reference](docs/HARDWARE.md). Do not flash a look-alike board or a different MCU.
2. Download the Windows installer from **Releases** when a reviewed beta package is posted. Keep all files together and run `KeypadOpenInstaller.exe`.
3. Follow its four steps: match the board, enter R12 bootloader mode, run the read-only check, then explicitly approve erase/flash/verify. Wait for **Verify OK** before reconnecting normally.

The installer never changes USB drivers. It can optionally download a checksum-pinned `wchisp` from its [upstream project](https://github.com/ch32-rs/wchisp); that tool is not bundled. The Windows app is unsigned, so Windows may ask you to confirm before opening it. See the [Windows package guide](firmware/flasher/WINDOWS_PACKAGE.md) if bootloader detection fails.

After flashing, use [Keypad Studio](https://github.com/jonassvidras/keypad-studio) to assign keys, shortcuts, media controls, clicks, scrolling, and 12 lighting modes. Settings save on the keypad.

## For builders

The pinned v2 image is `firmware/release/KeypadOpen-v2.hex` (SHA-256 `631c148775cec49ad15d1b5c2ae9d164493c9ff42332eb0aa6210d0e39fd8da5`). Its Intel HEX records match the owner-tested build; only text line endings changed. The earlier v1 image remains in `firmware/release/` for recovery; neither image restores factory firmware. Source and Windows build instructions are in `firmware/KeypadOpen/` and `firmware/build.ps1`. The build uses [CH55xDuino](https://github.com/DeqingSun/ch55xduino) 0.0.25; its LGPL-2.1 license remains its own. The optional `wchisp` tool also remains under its [upstream license](https://github.com/ch32-rs/wchisp/blob/main/LICENSE) and is not included here.

The firmware retains CH55xDuino's shared `1209:C55D` USB ID. Other devices using that ID may conflict with its Windows driver association; check the device and driver before flashing. Our original source is [MIT licensed](LICENSE); [third-party components](THIRD_PARTY.md) keep their own licenses. This repository is separate from Keypad Studio and contains no factory firmware backup.
