"""Build script for platform-epic8.

epic-cc is a whole-program compiler (epic-cc docs/31 D-7): every C source
goes into one invocation, so there are no per-object compile rules and no
linker. This script collects the project sources and hands them to epic-cc
in a single command.
"""

import json
import os
import subprocess
import sys
from os.path import join

from SCons.Script import AlwaysBuild, Default, DefaultEnvironment

env = DefaultEnvironment()
board = env.BoardConfig()

# Honor build_flags from platformio.ini. Only -D and -I are forwarded to
# epic-cc; other flags (optimization, warnings) are ignored because the
# compiler owns its invocation (docs/31 D-7).
env.ProcessFlags(env.get("BUILD_FLAGS"))

mcu = board.get("build.mcu", "")
if not mcu:
    sys.stderr.write("Error: board %s has no build.mcu\n" % board.id)
    env.Exit(1)

toolchain_dir = env.PioPlatform().get_package_dir("toolchain-epiccc")
if not toolchain_dir:
    sys.stderr.write("Error: toolchain-epiccc is not installed\n")
    env.Exit(1)
epiccc = join(toolchain_dir, "epic-cc")

# Framework wiring. When `framework = epichal` is set, the epic-hal
# framework package joins the build: the board's MCU picks the family,
# and EPIC_HAL_MODULES (a comma-separated build flag) picks the modules.
# epic-cc is a whole-program compiler, so the framework sources are
# compiled in, not linked (docs/31 D-7).
FRAMEWORK_FAMILY = {
    "p16f877a": "pic16f87xa",
    "p16f887": "pic16f88x",
    "p18f4550": "pic18fxx5x",
}


def _framework(env, mcu):
    if "epichal" not in env.get("PIOFRAMEWORK", []):
        return [], [], []
    fw_dir = env.PioPlatform().get_package_dir("framework-epichal")
    if not fw_dir:
        # Fall back to the shared packages dir: a locally installed or
        # manually placed framework package is not in the platform's
        # package registry, but still lives under ~/.platformio/packages.
        fw_dir = join(os.path.expanduser("~"), ".platformio", "packages", "framework-epichal")
    if not os.path.isdir(fw_dir):
        sys.stderr.write("Error: framework-epichal is not installed\n")
        env.Exit(1)
    slug = FRAMEWORK_FAMILY.get(mcu)
    if not slug:
        sys.stderr.write("Error: no epic-hal family for board MCU %s\n" % mcu)
        env.Exit(1)
    manifest = json.load(open(join(fw_dir, "epic-hal-sources-%s.json" % slug)))
    # Family includes, /target -> /epiccc for the epic-cc path (the
    # epic-cc SFR layer lives under include/epiccc, not include/target).
    includes = [
        join(fw_dir, d.replace("/target", "/epiccc"))
        for d in manifest["family_includes"]
    ]
    # The epic-cc path links the conformant source slice, not the full
    # XC8 set (which uses XC8-only syntax and exceeds the 877A's GPR
    # capacity). The framework package records it as epiccc_sources.
    hal_sources = manifest.get("epiccc_sources") or manifest["hal_sources"]
    sources = [join(fw_dir, s) for s in hal_sources]
    # Selected modules come from -DEPIC_HAL_MODULES=a,b; the framework
    # package is optional, so a project that never sets it stays bare.
    selected = []
    for d in env.get("CPPDEFINES", []):
        if isinstance(d, (tuple, list)) and d[0] == "EPIC_HAL_MODULES":
            selected = [m.strip() for m in d[1].split(",") if m.strip()]
    if not selected:
        sys.stderr.write(
            "Error: framework=epichal needs -DEPIC_HAL_MODULES=<modules>\n"
        )
        env.Exit(1)
    modules = manifest["modules"]
    resolved = set()
    for name in selected:
        key = name if name.startswith("epic-") else "epic-" + name
        if key not in modules:
            sys.stderr.write("Error: unknown epic-hal module %s\n" % name)
            env.Exit(1)
        resolved.update(modules[key]["resolved"])
    for key in sorted(resolved):
        sources += [join(fw_dir, s) for s in modules[key]["sources"]]
        includes += [join(fw_dir, d) for d in modules[key]["includes"]]
    # The HAL picks the device and the epic-cc SFR layer from these.
    defines = ["-DPIC%s" % mcu.upper(), "-D__EPIC_CC__"]
    return sources, includes, defines


fw_sources, fw_includes, fw_defines = _framework(env, mcu)

# Real source paths, not variant-dir copies: epic-cc reads the files
# directly, there is no per-object step to land in the build dir. The
# project lib/ dir joins the sources: a whole-program compiler takes every
# C file at once, so project libraries are compiled in, not linked.
lib_dir = join(env.subst("$PROJECT_DIR"), "lib")
sources = [
    env.File(join(env.subst("$PROJECT_SRC_DIR"), item))
    for item in env.MatchSourceFiles("$PROJECT_SRC_DIR", env.get("SRC_FILTER"), ["c"])
]
sources += [
    env.File(join(lib_dir, item))
    for item in env.MatchSourceFiles(lib_dir, env.get("SRC_FILTER"), ["c"])
]
sources += [env.File(s) for s in fw_sources]
if not sources:
    sys.stderr.write(
        "Error: no C sources found in %s\n" % env.subst("$PROJECT_SRC_DIR")
    )
    env.Exit(1)

defines = []
for d in env.get("CPPDEFINES", []):
    if isinstance(d, (tuple, list)):
        defines.append("-D%s=%s" % (d[0], d[1]))
    else:
        defines.append("-D%s" % d)
defines += fw_defines

# Include dirs: the project include/, src/ and lib/ dirs plus every
# CPPPATH entry, where build_flags -I lands. Deduped so a dir listed twice
# is passed once.
include_dirs = [
    env.subst("$PROJECT_INCLUDE_DIR"),
    env.subst("$PROJECT_SRC_DIR"),
    lib_dir,
]
for d in env.get("CPPPATH", []):
    d = env.subst(str(d))
    if d and d not in include_dirs:
        include_dirs.append(d)
for d in fw_includes:
    if d not in include_dirs:
        include_dirs.append(d)


def _epiccc(target, source, env):
    cmd = [epiccc, "--target", mcu, "-o", str(target[0])]
    for d in include_dirs:
        cmd += ["-I", d]
    cmd += defines
    cmd += [str(s) for s in source]
    print("epic-cc %s" % " ".join(cmd))
    return subprocess.call(cmd)


if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

firmware = env.Command(join("$BUILD_DIR", "${PROGNAME}.hex"), sources, _epiccc)

# Header edits must rebuild the HEX: SCons only tracks listed sources, and
# epic-cc reads headers through -I, so depend on every header under the
# include, src and project lib dirs.
def _headers(env, src_dir):
    return [
        env.File(join(env.subst(src_dir), item))
        for item in env.MatchSourceFiles(src_dir, env.get("SRC_FILTER"), ["h"])
    ]


header_deps = _headers(env, "$PROJECT_INCLUDE_DIR") + _headers(env, "$PROJECT_SRC_DIR")
header_deps += _headers(env, lib_dir)
# Framework headers too: the HAL and module headers live in the framework
# package, and an edit there must rebuild the HEX.
for d in fw_includes:
    header_deps += [
        env.File(join(d, item))
        for item in env.MatchSourceFiles(d, env.get("SRC_FILTER"), ["h"])
    ]
env.Depends(firmware, header_deps)

AlwaysBuild(env.Alias("buildprog", firmware, firmware))

# Upload. Two independent paths, chosen by board.upload.protocol (or
# UPLOAD_PROTOCOL in platformio.ini): `minipro` for a TL866A / TL866II
# Plus (GPL, fully independent of Microchip), `pk2cmd` for PICkit2 /
# PICkit3 / "PICkit3.5" / PKOB clones (Microchip's own licensed tool,
# see docs/pk2cmd-LICENSE.md: not MIT, fetched unmodified, never
# vendored into this repo's own code, same posture this project already
# takes with gpasm). Neither tool has a Debian/Ubuntu package. minipro
# finds a binary the user already built; pk2cmd defaults to where
# scripts/install-pk2cmd.sh installs it, since that script exists
# specifically to make setup straightforward without a build step.
import shutil


def _upload_minipro(source):
    binary = os.environ.get("EPIC8_MINIPRO_PATH") or shutil.which("minipro")
    if not binary:
        sys.stderr.write(
            "Error: minipro not found on PATH. Build it from "
            "https://gitlab.com/DavidGriffith/minipro (no Debian/Ubuntu "
            "package exists) and either put it on PATH or point "
            "EPIC8_MINIPRO_PATH at the binary. See "
            "docs/getting-started.md#upload.\n"
        )
        return 1
    device = board.get("upload.minipro_device", "")
    if not device:
        sys.stderr.write(
            "Error: board %s has no upload.minipro_device\n" % board.id
        )
        return 1
    cmd = [binary, "-p", device, "-w", str(source[0])]
    print("minipro %s" % " ".join(cmd[1:]))
    return subprocess.call(cmd)


# scripts/install-pk2cmd.sh's install location; the device database
# (PK2DeviceFile.dat) lives alongside the binary there, and pk2cmd's -B
# flag points it at that directory explicitly so it works regardless of
# the caller's cwd or where the binary itself is invoked from.
PK2CMD_DEFAULT_DIR = join(
    os.path.expanduser("~"), ".local", "share", "epic8", "pk2cmd"
)


def _upload_pk2cmd(source):
    device_dir = os.environ.get("EPIC8_PK2CMD_DIR", PK2CMD_DEFAULT_DIR)
    binary = (
        os.environ.get("EPIC8_PK2CMD_PATH")
        or shutil.which("pk2cmd")
        or join(device_dir, "pk2cmd")
    )
    if not os.path.isfile(binary):
        sys.stderr.write(
            "Error: pk2cmd not found. Run scripts/install-pk2cmd.sh "
            "(reads docs/pk2cmd-LICENSE.md before you use it: pk2cmd is "
            "Microchip's own licensed tool, not MIT), or point "
            "EPIC8_PK2CMD_PATH at a binary you already have. See "
            "docs/getting-started.md#upload.\n"
        )
        return 1
    device = board.get("upload.pk2cmd_device", "")
    if not device:
        sys.stderr.write(
            "Error: board %s has no upload.pk2cmd_device\n" % board.id
        )
        return 1
    cmd = [
        binary,
        "-B" + device_dir,
        "-P" + device,
        "-F" + str(source[0]),
        "-M",
    ]
    print("pk2cmd %s" % " ".join(cmd[1:]))
    return subprocess.call(cmd)


UPLOAD_PROTOCOLS = {"minipro": _upload_minipro, "pk2cmd": _upload_pk2cmd}


def _upload(target, source, env):
    protocol = env.get("UPLOAD_PROTOCOL") or board.get("upload.protocol", "")
    handler = UPLOAD_PROTOCOLS.get(protocol)
    if handler is None:
        sys.stderr.write(
            "Error: upload protocol %r is not supported by platform-epic8. "
            "Supported: %s\n"
            % (protocol or "(none)", ", ".join(sorted(UPLOAD_PROTOCOLS)))
        )
        return 1
    return handler(source)


AlwaysBuild(env.Alias("upload", firmware, _upload))
AlwaysBuild(env.Alias("program", firmware, _upload))

# Size report. epic-cc emits the whole flash image, so usage cannot be
# derived from the HEX; the compiler's own report (CC-6) is the source,
# and the released toolchain does not print it yet.
def _size(target, source, env):
    print(
        "Size: not reported; needs epic-cc size reporting (CC-6), "
        "not in the released toolchain"
    )
    return 0


AlwaysBuild(env.Alias("size", firmware, _size))

Default(firmware)
