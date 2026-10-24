# macOS read-only check

Mac flashing is **not yet validated**. This procedure only checks whether a
browser can read the keypad's USB bootloader identity. It cannot erase, flash,
or reset the keypad.

1. Compare the PCB with [the supported-board reference](../docs/HARDWARE.md).
2. In Terminal at the repository root, run:

   ```sh
   python3 -m http.server 8768 --bind 127.0.0.1 --directory firmware/flasher
   ```

3. Open `http://127.0.0.1:8768/mac-probe.html` in desktop Chrome or Edge.
   Unplug USB, bridge only the empty R12 pads while connecting USB-C, then
   release. Click **Connect and check device** and select `4348:55E0`.
4. Save the result, then unplug. Do not run the separate flashing installer.

If the bootloader times out, unplug and repeat the R12 entry. Do not short
individual MCU pins or bridge pads while powered. A successful read-only
check is not evidence that flashing will work or that another PCB is safe.
