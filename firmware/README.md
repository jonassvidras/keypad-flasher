# KeypadOpen firmware

KeypadOpen v2 is an owner-tested replacement for one measured CH552G three-key
keypad. It supports six configurable controls (three keys, encoder push, left,
right), keyboard shortcuts, media keys, mouse clicks and scrolling, plus 12 RGB
lighting modes. Settings persist in onboard data flash. There are no onboard
layers or macros. The v2 image is `release/KeypadOpen-v2.hex`; v1 is kept only
for recovery. Neither image restores the factory program.

The image is pinned by SHA-256
`631c148775cec49ad15d1b5c2ae9d164493c9ff42332eb0aa6210d0e39fd8da5`
and was reported working on one keypad after a USB reconnection. It has not
been validated on other PCB revisions. See [the board map](../docs/HARDWARE.md)
and the [flasher guide](flasher/README.md). The release repository's root README
has the short buyer-facing quick start.

The firmware exposes a `1209:C55D` composite USB HID device with a vendor Raw
HID collection (usage `FF60:0061`). [Keypad Studio](https://github.com/jonassvidras/keypad-studio)
uses this collection to read and save mappings and lighting with read-back.
The current build inherits CH55xDuino's USB product string `CH55xduino qmk kbd`
and manufacturer string `Deqing`. These can be changed in the build-time USB
descriptor, but that creates a new HEX requiring another hardware test. The
`1209:C55D` identity is registered to CH55xDuino, not this project. Before a
broad public binary release, confirm its use is acceptable or obtain a
project-specific PID. Changing the PID also requires a matching Studio update.

To build on Windows, install Arduino CLI 1.4.1 and CH55xDuino 0.0.25, then run
`firmware/build.ps1` from the project root. The build script compiles only; it
does not flash. Compare the resulting HEX with the pinned image before using
it. CH55xDuino is downloaded separately and retains its LGPL-2.1 license.

```powershell
arduino-cli core install CH55xDuino:mcs51@0.0.25 --additional-urls https://raw.githubusercontent.com/DeqingSun/ch55xduino/ch55xduino/package_ch55xduino_mcs51_index.json
.\firmware\build.ps1
python .\firmware\preflight.py .\firmware\release\KeypadOpen-v2.hex
```

The source in `KeypadOpen/` uses the measured GPIO map and CH55xDuino's USB
transport at build time. The release snapshot does not copy the vendor's
firmware, stock settings, CH55xDuino core, or `wchisp` binary.
