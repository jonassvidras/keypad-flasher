# Third-party components

The KeypadOpen HEX is built using [CH55xDuino 0.0.25](https://github.com/DeqingSun/ch55xduino/releases/tag/0.0.25),
which is licensed under [LGPL-2.1](LICENSES/CH55xDuino-LGPL-2.1.txt).
`firmware/build.ps1` copies selected core
files at build time and applies the USB descriptor and media-report changes
shown in that script. The core source is not copied into this repository.
The source archive offered alongside each Windows binary release includes the
CH55xDuino 0.0.25 core archive, our build script with its USB changes, and the
rebuildable KeypadOpen source. The
[upstream core archive](https://github.com/DeqingSun/ch55xduino/releases/download/0.0.25/ch55xduino-core-0.0.25.tar.bz2)
has SHA-256 `cc6ada6eb799b947756a2e0136424ed91890abd0cbbeec41775f017cce420887`.

The optional flashing backend is [wchisp](https://github.com/ch32-rs/wchisp),
licensed separately under GPL-2.0. Its executable is not bundled in this
repository or Windows installer. The user may opt into a checksum-verified
download directly from its upstream release.

The MIT license in this repository covers our original source and does not
replace either upstream license.
