# Flashing with minipro (XGecu T48, TL866II Plus)

`upload_protocol = minipro` (the default) drives an XGecu universal
programmer through [minipro](https://gitlab.com/DavidGriffith/minipro)
0.7.4, packaged as `tool-minipro`. The TL866CS has no ICSP header and
cannot be used.

## Wiring

Seat the chip in the programmer's ZIF socket, or wire its ICSP header to
the target: VPP, VDD, GND, PGD, PGC, plus PGM for parts that program with
LVP. The beta boards name the PGM pin in `upload.hazards.pgm_pin`
(18F4550 RB5, 877A and 887 RB3, 628A RB4); the 1937 uses a key sequence
and the 12F675 has no LVP.

## Install

Selecting the protocol pulls `tool-minipro` automatically. To use your
own build instead, put it on `PATH` or point `EPIC8_MINIPRO_PATH` at it.
Either way the device databases (`infoic.xml`, `logicic.xml`) must be
visible: the package sets that up, a hand build needs `make install`.

## udev

```bash
sudo cp udev/99-epic8.rules /etc/udev/rules.d/
sudo udevadm trigger
```

Then replug the programmer. Your user must be in `plugdev`.

## First flash

```bash
pio run -t upload                # write firmware.hex to the chip
pio run -t erase                 # bulk erase
pio run -t readback              # dump flash to .pio/build/<env>/readback.hex
```

## Troubleshooting

- `No programmer found`: udev rules missing or the replug skipped. Check
  `lsusb` for `a466:0a53` (T48, TL866II Plus) or `04d8:e11c` (TL866A).
- `Chip ID mismatch`: the socket holds a different part than the board
  names. `minipro -p <device> -D` reads the ID without touching flash.
- A part missing from `minipro -l` is a device-database gap upstream,
  not a wiring fault: report it to the minipro project with the database
  spelling attached (agents: file a `dispatch-only` issue here instead).
