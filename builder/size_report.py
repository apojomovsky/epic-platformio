"""Print the driver's build report in the columns PlatformIO's size check wants.

epic-cc is a whole-program compiler: no ELF, no symbol table, so
PlatformIO's ELF-based size tool cannot read its output. The driver's
`--report` JSON is the source of truth (ADR-025), and this renders it as
the single line `CheckUploadSize` parses with SIZEPROGREGEXP and
SIZEDATAREGEXP:

    <flash_used_bytes> <flash_total_bytes> <ram_used_bytes> <ram_total_bytes>

Flash is words times two, since a board's `maximum_size` is bytes and HEX
addresses are byte addresses (docs/46 D-7). A real script, invoked by
path, not an inline `python -c`: `CheckUploadSize` splits SIZECHECKCMD on
whitespace, so a command carrying spaces would never run.

Usage:
    size_report.py <build-report.json>
"""

import json
import sys


def main(path: str) -> int:
    report = json.load(open(path))
    flash = report["flash_words"]
    ram = report["ram_bytes"]
    print(
        "%d %d %d %d"
        % (flash["used"] * 2, flash["total"] * 2, ram["used"], ram["total"])
    )
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: size_report.py <build-report.json>\n")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
