# KeypadOpen v2 installer · Windows 11 beta

This folder contains the local installer and the pinned KeypadOpen v2 image.
The owner tested v2 on one CH552G keypad. Other boards from the same listing
may be wired differently. The factory firmware cannot currently be restored.
See `LICENSE` and `THIRD_PARTY.md` for source and dependency notices.

1. Compare your PCB to the board diagram in the installer. Stop if its CH552G,
   empty R12 pads, LEDs, or encoder do not match.
2. Run `KeypadOpenInstaller.exe`. It opens a local browser page. If needed,
   choose **Download verified wchisp**; the download is optional, hash-checked,
   and does not install a driver.
3. Follow the page: enter R12 bootloader mode, use the read-only **Check device**
   button, acknowledge stock-firmware loss, then **Erase, flash and verify**.
   Wait for `Verify OK` before unplugging. Reconnect without bridging R12.

The installer accepts only the included v2 HEX (SHA-256
`631c148775cec49ad15d1b5c2ae9d164493c9ff42332eb0aa6210d0e39fd8da5`)
and a CH552 with bootloader 02.50. These checks do not prove board wiring.
Never flash merely because the USB ID or MCU matches. If a step fails, stop
and keep the log; do not repeatedly erase or try another image. The log may
contain your chip UID or Windows device instance ID; review it before sharing.

`wchisp.exe` is not bundled. The optional download comes from the
[upstream project](https://github.com/ch32-rs/wchisp), is pinned by archive
and executable hashes, and may stop working if its upstream nightly changes.
Windows needs a working WCH or WinUSB driver for bootloader `4348:55E0`;
this installer never changes drivers. See [upstream Windows guidance](https://github.com/ch32-rs/wchisp#note-for-windows).
