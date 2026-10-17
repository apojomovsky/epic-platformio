# Debugging with `pio debug`

This page is for you if your project builds on one of the simulator boards
(`pic16f877a`, `pic16f887`, `pic16f628a`, `pic12f675`, `pic18f4550`) and
you want breakpoints, stepping, and typed variables instead of LEDs.
Debugging runs the program in epic-cc's own simulator on your machine,
not on the chip: no programmer involved.

## Prerequisites

- A simulator board: `pic16f877a`, `pic16f887`, `pic16f628a`,
  `pic12f675`, or `pic18f4550`. Other parts follow their own epic-cc
  debugger support; a board without a debug section fails with
  PlatformIO's "does not support debugging".
- Stock gdb on PATH (`apt install gdb` on Debian/Ubuntu). A packaged gdb
  is a separate child; until it lands, the client is the system one.
- A current `toolchain-epiccc` ([package versions](../packages.md)),
  which ships `epic-cc-gdbserver`. `pic18f4550` needs one built from
  epic-cc 0.5.0 or later: older servers predate `--device` and fail at
  server start on a pic18 board.

No `platformio.ini` setup is needed: the board selects `debug_tool =
epic-sim` by default.

## A first session

The `examples/debug-pic16f877a` project is the smallest program worth
debugging: one global, one local, straight-line code that runs to the end
and sleeps. Copy it and start `pio debug --interface gdb`:

```console
(gdb) target remote :3333
Remote debugging using :3333
0x00000000 in ?? ()
(gdb) break main.c:29
Breakpoint 1 at 0x9: file main.c, line 29.
(gdb) continue
Continuing.

Breakpoint 1, ?? () at main.c:29
29	    g_a = tmp + 1;
(gdb) print tmp
$1 = 41
(gdb) next
30	    PORTB = (uint8_t)g_a;
(gdb) print g_a
$2 = 42
(gdb) info line
Line 30 of "main.c" starts at address 0x19 and ends at 0x1a.
(gdb) continue
Continuing.

Program terminated with signal SIGKILL, Killed.
The program no longer exists.
```

The session starts halted at the reset vector, so connect and set your
breakpoints before continuing. `print` reads globals and locals by C name,
`next` steps a source line, `info line` names the current one. Running
past the last line ends the program: falling off `main` sleeps the sim,
which the server reports as termination.

## Stopping on launch

Uncomment the `debug_init_break` line in the example (or set your own) to
stop at a C line as soon as the session opens:

```ini
debug_init_break = tbreak main.c:29
```

The value is one gdb command, so `file:line` is the shape that resolves.
Use `tbreak`, not `thbreak`: the server offers software breakpoints only,
so a hardware breakpoint is rejected. Function names do not resolve
either: the sidecar carries line rows and typed variables but no
subprogram entries, so `tbreak main` never resolves and the default stays
empty on purpose.

## Which code debugs cleanly

The -Os line rows cover straight-line code over locals and globals. Calls,
loops, and bank-switched SFR setup misattribute the lines after them:
a breakpoint there lands on a word that never executes, so `continue`
runs past it. Keep first sessions to the example's shape; the row gaps
are tracked in epic-cc#1316.

## PlatformIO IDE

Open the project in VS Code with the PlatformIO IDE extension and run
Start Debugging. It drives the same server and the same init script as
`pio debug`: set breakpoints in the editor gutter, then Continue from the
halted entry. Restarting replays from the reset vector with a fresh
simulator; there is no reset-while-running, the server serves one session
and exits.

## Reference

- The server is `epic-cc-gdbserver` from the toolchain package, run on
  the built hex file plus the ELF+DWARF sidecar the builder always emits
  next to it (`firmware.elf` beside `firmware.hex` in the build dir). A
  board off the default pic14 sim (today, `pic18f4550`) adds
  `--device <mcu>`; pic14 boards spell none. gdb loads the sidecar,
  never the hex file.
- An XC8 build (`board_build.toolchain = xc8`) is refused up front: it
  emits no sidecar, so there is nothing for the server to load.
- Troubleshooting: `No gdb on PATH` means install gdb above. A
  `Permission denied` launching the server means the installed toolchain
  package predates the executable-bit fix shipped in [later
  packages](../packages.md): until the update lands, `chmod +x` the
  `epic-cc-gdbserver` binary in the toolchain package dir and retry.
