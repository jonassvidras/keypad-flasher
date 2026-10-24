# Supported board reference

This firmware targets one measured CH552G three-key keypad layout. A CH552G
identity alone does not establish compatibility: similar keypads can use other
GPIO assignments and LED wiring. The installer includes a code-drawn reference
diagram, not a photograph or proof of a specific board revision.

| Function | CH552G GPIO | SOP-16 pin |
| --- | --- | ---: |
| Key 1 / U1 | P1.1 | 9 |
| Key 2 / U2 | P1.7 | 5 |
| Key 3 / U3 | P1.6 | 4 |
| Encoder push | P3.3 | 10 |
| Encoder A | P3.0 | 8 |
| Encoder B | P3.1 | 7 |
| LED data | P3.4, through R17 (1 kΩ) | 11 |
| LED supply | VCC | 15 |
| Ground | GND | 14 |

The three addressable LEDs are connected in physical data order D7 → D6 → D5.
The unpopulated R12 footprint provides the tested bootloader-entry bridge;
with USB unplugged, bridge those two pads while plugging in, then release.
Do not short MCU pins directly. The USB ISP device identifies as `4348:55E0`
and the measured bootloader version is `02.50`.

Before replacing stock firmware on another unit, verify its component
designators and wiring rather than relying on the listing, enclosure, or USB
identity. The stock application has no recoverable firmware backup in this
project; its data-EEPROM dump is only settings.
