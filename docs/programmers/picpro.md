# Flashing with picpro (K150 and siblings)

`upload_protocol = picpro` drives a Kitsrus K150, K128, K149 or K182
through [picpro](https://github.com/Salamek/picpro) 0.4.1, packaged as
`tool-picpro` and run under PlatformIO's own interpreter. It covers four
beta parts (877A, 628A, 12F675, 4550); the 16F887 and 16F1937 have no
picpro entry, so those boards refuse the protocol naming the tools that
do.

## Wiring

Seat the chip in the K150 ZIF socket. The K150 reaches the host as a
serial device (`/dev/ttyUSB0` typically); name it with `upload_port`:

```ini
upload_protocol = picpro
upload_port = /dev/ttyUSB0
```

## Firmware prerequisite

The K150 must speak protocol P18A. Older firmware (P018, P016, P014 or
earlier) is not supported by picpro. Check what yours speaks:

```bash
picpro programmer_info -p /dev/ttyUSB0
```

A unit on old firmware needs a reflash with P18A firmware before
anything below works.

## Install

`tool-picpro` will pull automatically once its release lands
(epic-platformio#43); until then use your own install
(`pip install picpro`) on `PATH` or point `EPIC8_PICPRO_PATH` at it.

## udev

```bash
sudo cp udev/99-epic8.rules /etc/udev/rules.d/
sudo udevadm trigger
```

Then replug the adapter. Your user must be in `plugdev`. K150 clones
vary their USB-serial chip (CH340, PL2303, FTDI); the rules cover all
three, and `lsusb` tells you which yours is.

## First flash

```bash
pio run -t upload                # program the chip
pio run -t erase                 # bulk erase
pio run -t readback              # dump ROM to .pio/build/<env>/readback.hex
```

`upload_flags` appends tool arguments, e.g. `upload_flags = --icsp`.

## Troubleshooting

- `upload_protocol=picpro needs upload_port`: the serial device is a
  project setting, not auto-detected. Set `upload_port`.
- `Unable to locate chipinfo.cid file`: a hand install whose data file
  is missing. The tool package carries it.
- No device entry for your part (`upload.devices.picpro` absent): picpro
  genuinely has no support for it. Use minipro or pk2cmd.
