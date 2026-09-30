# Flashing with pk2cmd (PICkit2, PICkit3, PKOB)

`upload_protocol = pk2cmd` drives a PICkit2, PICkit3, PKOB, or a
"PICkit3.5" clone (clone-vendor branding for the PICkit3 protocol)
through [jaka-fi/pk2cmd](https://github.com/jaka-fi/pk2cmd) 1.27.01,
packaged as `tool-pk2cmd`. That fork is the maintained one;
`cjacker/pk2cmd-minus` is idle since 2023.

The package ships Microchip's own `PK2DeviceFile.dat` 1.62.14, not
jaka-fi's, which jaka-fi withdrew after a copyright claim from the
PICkitPlus team (`docs/platform-decisions.md`). It covers every board in
`boards/`. Newer MSB-first (MSB1st) parts, such as the PIC16F18xxx and
PIC18 Q families, are not in it; see "Parts outside the bundled device
file" below.

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

## Parts outside the bundled device file

`pk2cmd` rejects a part name its device file does not list. For such a
part, keep the packaged binary and point it at a device file that does
list it:

```ini
upload_flags = -B/path/to/devfile/dir
```

`-B` takes the directory holding `PK2DeviceFile.dat`. MSB-first parts need
a 2.63.222 or later file to work with jaka-fi's binary. Boards under
`boards-experimental/` carry no pk2cmd name, so add
`upload.devices.pk2cmd` (the file's exact `PartName`) to your copy of the
board first.

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

## Calibration data on the 12F629/675

The default flags preserve the factory OSCCAL word and bandgap bits:
pk2cmd reads them before the bulk erase and writes them back after
(epic-platformio#62, verified from source and the device file, not on
hardware). Appending `-U` in `upload_flags` cannot silently override
this: it needs `-M<value>`, but the platform's own bare `-M` comes
first on the command line, so pk2cmd exits with a usage error instead.

## Troubleshooting

- `PICkit 2/3/PKOB not found`: udev rules missing, or the clone
  firmware prerequisite above. Check `lsusb` for `04d8:0033` (PICkit2),
  `04d8:900a` (PICkit3), `04d8:8107` (PKOB).
- `PK2DeviceFile.dat device file not found`: a hand build without the
  DAT beside it. Point `-B` at its directory.
