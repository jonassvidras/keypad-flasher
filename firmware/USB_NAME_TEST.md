# Private USB-name test

This candidate changes only the USB product/manufacturer strings to
`KeypadOpen` / `KeypadOpen Project`. It retains `1209:C55D` and the v2
configuration protocol. It has compiled and passed image preflight, but has
**not** been flashed or hardware-tested. Do not publish this image yet.

The tested v2 image remains in `firmware/release/KeypadOpen-v2.hex`. Save or
export your Keypad Studio profile before the test. Keep the normal v2 flasher
available for recovery; neither image restores factory firmware.

1. At the project root on Windows 11, verify the candidate:

   ```powershell
   py -3 .\firmware\preflight.py .\firmware\build\usb-names\KeypadOpen.ino.hex
   ```

   Expect SHA-256 `89e26537091e8549df46e445f8ea0ab1f01506b89595f0301c633e034fedc8d6`,
   11,913 programmed bytes, and last address `0x2ED8`. Stop if any value differs.
2. Start the local installer in candidate mode:

   ```powershell
   py -3 .\firmware\flasher.py --usb-name-candidate --wchisp "$env:LOCALAPPDATA\KeypadOpen\tools\wchisp.exe"
   ```

   Confirm the page says **USB-name test** and displays that SHA-256. The
   installer checks the tool, image, board checklist, chip UID, and exact
   typed confirmation before writing. Enter R12 bootloader mode only as the
   page explains. Wait for **Verify OK** before reconnecting normally.
3. On reconnection, check that Windows reports the new names. Connect with
   Keypad Studio, read settings, change one LED setting, save it, and verify
   it survives unplug/replug. Test all three keys and knob left/right/push.

If the new image does not enumerate or work correctly, unplug, re-enter R12
bootloader mode, and run the normal `py -3 .\firmware\flasher.py` installer to
restore the owner-tested v2 image. Stop if the bootloader is not detected;
do not repeatedly erase. Report behavior without posting the chip UID or
complete device logs publicly.
