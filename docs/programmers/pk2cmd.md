# Flashing with pk2cmd (PICkit2, PICkit3, PKOB)

`upload_protocol = pk2cmd` drives a PICkit2, PICkit3, PKOB, or a
"PICkit3.5" clone (clone-vendor branding for the PICkit3 protocol)
through [jaka-fi/pk2cmd](https://github.com/jaka-fi/pk2cmd) 1.27.01,
packaged as `tool-pk2cmd` with its `PK2DeviceFile.dat`. That fork is the
maintained one; `cjacker/pk2cmd-minus` is idle since 2023.

pk2cmd is Microchip-licensed, not open source. Clause 1(b) permits
redistributing a modified version for use with Microchip products with
the copyright and modified-by notice shown; the package carries it in
`NOTICE.txt` and the binary prints it on every `-?` invocation.

## Wiring

Wire the PICkit ICSP header to the target: VPP/MCLR, VDD, GND, PGD, PGC.
The tool powers the target itself by default (`-W` for externally
powered targets).

## Firmware prerequisite

Some PICkit3 clones arrive with firmware no Linux tool drives. They need
a one-time update to the PK2-style scripting firmware, and only the
vendor's Windows updater can push it. Symptom: `pk2cmd` reports the
programmer as not found or not responding on first use. Run the updater
once on a Windows machine; the clone works under `pk2cmd` on Linux
thereafter.

## Install

Selecting the protocol pulls `tool-pk2cmd` automatically. To use your
own build instead, put it on `PATH` or point `EPIC8_PK2CMD_PATH` at it,
with `PK2DeviceFile.dat` beside the binary (or `-B<dir>` at it).

## udev

```bash
sudo cp udev/99-epic8.rules /etc/udev/rules.d/
sudo udevadm trigger
```

Then replug the programmer. Your user must be in `plugdev`.

## First flash

```bash
pio run -t upload                # program flash, config, erase first
pio run -t erase                 # bulk erase
pio run -t readback              # dump flash to .pio/build/<env>/readback.hex
```

`upload_flags` appends tool arguments, e.g. `upload_flags = -L4` slows
the ICSP clock for loaded PGx lines or long cables.

## Troubleshooting

- `PICkit 2/3/PKOB not found`: udev rules missing, or the clone
  firmware prerequisite above. Check `lsusb` for `04d8:0033` (PICkit2),
  `04d8:900a` (PICkit3), `04d8:8107` (PKOB).
- `PK2DeviceFile.dat device file not found`: a hand build without the
  DAT beside it. Point `-B` at its directory.
