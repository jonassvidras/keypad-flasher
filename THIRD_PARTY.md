# Third-party components

The KeypadOpen HEX is built using [CH55xDuino 0.0.25](https://github.com/DeqingSun/ch55xduino),
which is licensed under LGPL-2.1. `firmware/build.ps1` copies selected core
files at build time and applies the USB descriptor and media-report changes
shown in that script. The core source is not copied into this repository.
Before distributing a binary release, review the upstream license and make
sure recipients can obtain the corresponding core source and our build changes.

The optional flashing backend is [wchisp](https://github.com/ch32-rs/wchisp),
licensed separately under GPL-2.0. Its executable is not bundled in this
repository or Windows installer. The user may opt into a checksum-verified
download directly from its upstream release. macOS users must obtain their
own compatible build for the later supervised test.

The MIT license in this repository covers our original source and does not
replace either upstream license.
