#!/usr/bin/env python3
"""Guided hardware sign-off for the beta boards (epic-platformio#52).

Walks the board-by-programmer matrix from the ticket: T48 (minipro) and
PICkit 3.5 (pk2cmd) for all six boards, K150 (picpro) for the four parts
picpro knows. Each row prompts the human to fit the chip and programmer,
runs `pio run -e <env> -t upload` on the blink example with the row's
protocol (the env comes from the example's own platformio.ini),
then asks whether the LED blinked. Answers accumulate in
signoff-results.json, so an interrupted session resumes where it stopped.

The script never touches hardware on its own: every upload waits for the
human to fit parts first, and nothing here runs in CI. `--apply` flips
`support` to `hardware` for boards with at least one green row, through
gen_boards.py so the next regen keeps the level.
"""

from __future__ import annotations

import argparse
import configparser
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_RESULTS = pathlib.Path("signoff-results.json")

# The six beta boards (docs/46 D-2), in board JSON id order.
BOARDS = (
    "pic12f675",
    "pic16f1937",
    "pic16f628a",
    "pic16f877a",
    "pic16f887",
    "pic18f4550",
)

# picpro's device list covers four beta parts (docs/programmers/picpro.md):
# the 16F887 and 16F1937 have no entry, so those boards refuse the protocol.
PICPRO_BOARDS = frozenset(
    {"pic16f877a", "pic16f628a", "pic12f675", "pic18f4550"}
)

# Protocol rows are grouped by programmer so the human swaps hardware as
# rarely as possible: six T48 fits, then six PICkit fits, then four K150.
PROGRAMMERS = (
    ("minipro", "XGecu T48"),
    ("pk2cmd", "PICkit 3.5"),
    ("picpro", "K150"),
)

PICPRO_DEFAULT_PORT = "/dev/ttyUSB0"


def matrix() -> list[tuple[str, str]]:
    """(board, protocol) rows in the order the walk prompts them."""
    rows = []
    for protocol, _label in PROGRAMMERS:
        for board in BOARDS:
            if protocol == "picpro" and board not in PICPRO_BOARDS:
                continue
            rows.append((board, protocol))
    return rows


def row_key(board: str, protocol: str) -> str:
    return f"{board}/{protocol}"


def programmer_label(protocol: str) -> str:
    return dict(PROGRAMMERS)[protocol]


def example_dir(repo: pathlib.Path, board: str) -> pathlib.Path:
    # Every beta board has a blink-tutorial example (test_examples_config.py
    # pins the set); the older blink-pic* trio covers only three boards.
    return repo / "examples" / f"blink-tutorial-{board}"


def project_env(example: pathlib.Path) -> str:
    """First `[env:*]` section of the example's platformio.ini.

    The ticket writes `-e <board>`, but every blink example names its env
    `epic8`, so the script reads the ini instead of assuming the shorthand.
    """
    parser = configparser.ConfigParser()
    parser.read(example / "platformio.ini")
    for section in parser.sections():
        if section.startswith("env:"):
            return section[len("env:"):]
    raise ValueError(f"no [env:*] section in {example / 'platformio.ini'}")


def upload_command(env_name: str) -> list[str]:
    return ["pio", "run", "-e", env_name, "-t", "upload"]


def upload_environment(protocol: str, port: str | None) -> dict[str, str]:
    """Extra environment overriding the example's upload settings.

    PlatformIO lets `PLATFORMIO_<OPTION>` variables override project
    options, so the row's protocol applies without editing the example's
    ini. picpro additionally needs the K150 serial port (upload_port).
    """
    extra = {"PLATFORMIO_UPLOAD_PROTOCOL": protocol}
    if protocol == "picpro" and port is not None:
        extra["PLATFORMIO_UPLOAD_PORT"] = port
    return extra


def default_runner(
    cmd: list[str], cwd: pathlib.Path, extra_env: dict[str, str]
) -> int:
    """Run the upload, inheriting stdio so the human sees tool output."""
    import os

    env = dict(os.environ)
    env.update(extra_env)
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    return proc.returncode


def load_results(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"version": 1, "rows": {}}
    return json.loads(path.read_text())


def save_results(path: pathlib.Path, results: dict) -> None:
    path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")


def green_boards(results: dict) -> list[str]:
    """Boards with at least one row the human confirmed blinking."""
    boards = sorted(
        {
            key.split("/")[0]
            for key, verdict in results.get("rows", {}).items()
            if verdict == "pass"
        }
    )
    return [board for board in boards if board in BOARDS]


def ask_verdict(readline, output, board: str, protocol: str) -> str:
    """The blink question; anything but y/n/skip asks again."""
    while True:
        answer = readline(
            f"[{board} via {programmer_label(protocol)}] did it blink? y/n/skip "
        ).strip().lower()
        if answer in ("y", "yes"):
            return "pass"
        if answer in ("n", "no"):
            return "fail"
        if answer in ("skip", "s"):
            return "skip"
        output("answer y, n or skip.")


def ask_port(readline, previous: str | None) -> str:
    """The K150 serial port, remembered across rows and sessions."""
    default = previous or PICPRO_DEFAULT_PORT
    answer = readline(f"K150 serial port [{default}]: ").strip()
    return answer or default


def walk(
    repo: pathlib.Path,
    results: dict,
    runner=default_runner,
    readline=input,
    output=print,
) -> dict:
    """Prompt every undecided row: fit parts, upload, record the verdict."""
    rows = results.setdefault("rows", {})
    port = results.get("picpro_port")
    for board, protocol in matrix():
        key = row_key(board, protocol)
        if rows.get(key) in ("pass", "fail"):
            continue
        example = example_dir(repo, board)
        env_name = project_env(example)
        if protocol == "picpro" and port is None:
            port = ask_port(readline, port)
            results["picpro_port"] = port
        cmd = upload_command(env_name)
        extra = upload_environment(protocol, port)
        output(f"Fit the {board} chip and the {programmer_label(protocol)} programmer.")
        output(f"Running: {' '.join(cmd)} (cwd={example})")
        readline("Press Enter to upload, or Ctrl-C to stop here. ")
        code = runner(cmd, example, extra)
        if code != 0:
            output(f"Upload failed (exit {code}); recording fail for {key}.")
            output("Delete the row from the results file to retry it later.")
            rows[key] = "fail"
            continue
        rows[key] = ask_verdict(readline, output, board, protocol)
    return results


def set_hardware_boards(repo: pathlib.Path, boards: list[str]) -> None:
    """Rewrite HARDWARE_BOARDS in gen_boards.py so regens keep the level."""
    path = repo / "scripts" / "gen_boards.py"
    text = path.read_text()
    names = ", ".join(f'"{board}"' for board in sorted(boards))
    replacement = f"HARDWARE_BOARDS: frozenset = frozenset({{{names}}})"
    updated, count = re.subn(r"^HARDWARE_BOARDS.*$", replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("HARDWARE_BOARDS line not found in scripts/gen_boards.py")
    path.write_text(updated)


def apply_support(repo: pathlib.Path, boards: list[str]) -> list[str]:
    """Set support hardware in the green boards' JSON, reporting each."""
    applied = []
    wanted = set(boards)
    for board_file in sorted((repo / "boards").glob("pic*.json")):
        doc = json.loads(board_file.read_text())
        if board_file.stem in wanted and doc.get("support") != "hardware":
            doc["support"] = "hardware"
            board_file.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
            applied.append(board_file.stem)
    return applied


def cmd_list() -> int:
    for board, protocol in matrix():
        print(f"{row_key(board, protocol):28} {programmer_label(protocol)}")
    return 0


def cmd_walk(args) -> int:
    results = load_results(args.results)
    try:
        results = walk(REPO, results)
    finally:
        save_results(args.results, results)
    greens = green_boards(results)
    print(f"Green boards: {', '.join(greens) if greens else 'none yet'}.")
    print(f"Results in {args.results}; rerun to resume.")
    return 0


def cmd_apply(args) -> int:
    results = load_results(args.results)
    greens = green_boards(results)
    if not greens:
        print("No green rows, nothing to apply.")
        return 0
    set_hardware_boards(REPO, greens)
    applied = apply_support(REPO, greens)
    print(f"Hardware-proven boards: {', '.join(greens)}.")
    if applied:
        print(f"Updated support in: {', '.join(applied)}.")
    else:
        print("Board JSON already at hardware; generator set updated.")
    print("Then run: make docs-gen && git diff")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--results",
        default=DEFAULT_RESULTS,
        type=pathlib.Path,
        help="where row verdicts accumulate (default signoff-results.json)",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="print the board-by-programmer matrix and exit",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="set support hardware for boards with a green row, then exit",
    )
    args = ap.parse_args(argv)
    if args.list:
        return cmd_list()
    if args.apply:
        return cmd_apply(args)
    return cmd_walk(args)


if __name__ == "__main__":
    sys.exit(main())
