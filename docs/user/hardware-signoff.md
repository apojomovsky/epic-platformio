# Hardware sign-off

Before the beta announcement, every beta board must prove itself on real
silicon: flash its blink example with each programmer whose tool supports
the part, and watch the LED blink. A board with at least one confirmed
row ships as `hardware`; the rest stay `simulator`. The sign-off itself
is a human gate (D-11): this page and `scripts/hw_signoff.py` only guide
it, and nothing here runs in CI or touches hardware on its own.

## The matrix

T48 (`minipro`) and PICkit 3.5 (`pk2cmd`) cover all six boards; the K150
(`picpro`) covers the four parts in its device list. That is sixteen
rows: six plus six plus four. The 16F887 and 16F1937 have no picpro
entry, so those boards never get a K150 row. Programmer setup (drivers,
udev, the K150 P18A firmware prerequisite) is in `docs/programmers/`.

## Running the walk

```bash
python3 scripts/hw_signoff.py
```

For each row the script names the chip and programmer to fit, runs
`pio run -t upload` in the board's `blink-tutorial-*` example with the
row's protocol, then asks `did it blink? y/n/skip`. Rows run grouped by
programmer, so you swap hardware as rarely as possible. For K150 rows it
asks for the serial port once (default `/dev/ttyUSB0`) and reuses it.

Verdicts accumulate in `signoff-results.json` in the working directory.
Rerunning resumes where you stopped: decided rows are skipped, `skip`
rows are asked again. A failed upload records `fail` without asking;
delete that row from the file to retry it. Pass `--results <file>` to
keep the verdicts elsewhere, `--list` to print the matrix without
prompting anything.

## Applying the results

```bash
python3 scripts/hw_signoff.py --apply [--results <file>]
make docs-gen
```

`--apply` sets `support: hardware` in each green board's JSON and records
the set in `scripts/gen_boards.py` (`HARDWARE_BOARDS`), so the next board
regen keeps the level instead of resetting it to `simulator`.
`make docs-gen` refreshes the boards table, then open one pull request
from the results. Boards with no green row keep shipping as `simulator`.
