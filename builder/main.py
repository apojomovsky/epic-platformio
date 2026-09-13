"""Build script for platform-epic8.

epic-cc is a whole-program compiler (epic-cc docs/31 D-7): every C source
goes into one invocation, so there are no per-object compile rules and no
linker. XC8 is a fully supported alternate toolchain (`board_build.toolchain
= xc8`, default `epic-cc`): the ordinary compile-then-link shape, one object
per source file. XC8 is never vendored (Microchip's EULA forbids
redistribution, docs/platform-decisions.md), so this script finds a binary
the user already installed, on PATH or via EPIC8_XC8_PATH, the same pattern
already used for the upload tools below.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from os.path import join

from SCons.Script import AlwaysBuild, Default, DefaultEnvironment

env = DefaultEnvironment()
board = env.BoardConfig()

# Honor build_flags from platformio.ini. Only -D and -I are forwarded to
# epic-cc; other flags (optimization, warnings) are ignored because the
# compiler owns its invocation (docs/31 D-7). XC8 gets its own fixed flag
# set below (build_flags -D/-I still apply, -O/-W do not, matching epic-cc's
# posture: the toolchain owns its own invocation either way).
env.ProcessFlags(env.get("BUILD_FLAGS"))

mcu = board.get("build.mcu", "")
if not mcu:
    sys.stderr.write("Error: board %s has no build.mcu\n" % board.id)
    env.Exit(1)

# platform-epic8 spells the board mcu with a leading "p" (epic-cc's own
# --target spelling, e.g. "p16f877a"); XC8's -mcpu= and the HAL's PIC<part>
# device-selection macros both want the bare device name epic-hal itself
# uses ("16f877a"/"PIC16F877A", no leading "p"). Strip it once, here.
bare_mcu = mcu[1:] if mcu[:1].lower() == "p" else mcu

toolchain = board.get("build.toolchain", "epic-cc")
if toolchain not in ("epic-cc", "xc8"):
    sys.stderr.write(
        "Error: board_build.toolchain %r is not supported. "
        "Supported: epic-cc (default), xc8\n" % toolchain
    )
    env.Exit(1)

epiccc = None
xc8cc = None
xc8_dfp_dir = ""
if toolchain == "epic-cc":
    toolchain_dir = env.PioPlatform().get_package_dir("toolchain-epiccc")
    if not toolchain_dir:
        sys.stderr.write("Error: toolchain-epiccc is not installed\n")
        env.Exit(1)
    epiccc = join(toolchain_dir, "epic-cc")
else:
    # Never vendored (EULA forbids redistribution): found via PATH or an
    # env var override, exactly like minipro/pk2cmd below.
    xc8cc = os.environ.get("EPIC8_XC8_PATH") or shutil.which("xc8-cc")
    if not xc8cc:
        sys.stderr.write(
            "Error: xc8-cc not found on PATH. Install MPLAB XC8 (free tier "
            "is enough) from "
            "https://www.microchip.com/en-us/tools-resources/develop/mplab-xc-compilers "
            "and either put its bin/ on PATH or point EPIC8_XC8_PATH at the "
            "xc8-cc binary. See docs/getting-started.md#xc8.\n"
        )
        env.Exit(1)
    # Optional: only needed for a device family whose headers/support files
    # aren't in XC8's own built-in set. Unset means "no -mdfp", matching
    # epic-hal's own epic_build.py --dfp-dir default.
    xc8_dfp_dir = os.environ.get("EPIC8_XC8_DFP_DIR", "")

# Framework wiring. When `framework = epichal` is set, the epic-hal
# framework package joins the build: the board's MCU picks the family,
# and EPIC_HAL_MODULES (a comma-separated build flag) picks the modules.
# Under epic-cc (a whole-program compiler, docs/31 D-7) the framework
# sources are compiled in, not linked; under xc8 they're just more
# translation units in the ordinary compile-then-link build below.
FRAMEWORK_FAMILY = {
    "p16f877a": "pic16f87xa",
    "p16f887": "pic16f88x",
    "p18f4550": "pic18fxx5x",
}


def _framework(env, mcu, toolchain):
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
    device = bare_mcu.upper()
    if toolchain == "epic-cc":
        # Family includes, /target -> /epiccc for the epic-cc path (the
        # epic-cc SFR layer lives under include/epiccc, not include/target).
        includes = [
            join(fw_dir, d.replace("/target", "/epiccc"))
            for d in manifest["family_includes"]
        ]
        # The epic-cc path links the conformant source slice, not the full
        # XC8 set (which uses XC8-only syntax and exceeds the 877A's GPR
        # capacity). The framework package records it as epiccc_sources.
        # conditional_sources never applies here (epic-hal's own reference
        # resolution, epicmanifest.py Manifest.sources_for, only interleaves
        # them into the real hal_sources list below): the epiccc slice is a
        # curated, GPR-budget-checked set, and a per-device peripheral file
        # was never vetted against it.
        hal_sources = manifest.get("epiccc_sources") or manifest["hal_sources"]
        sources = [join(fw_dir, s) for s in hal_sources]
        # The HAL picks the device and the epic-cc SFR layer from these.
        defines = ["-DPIC%s" % device, "-D__EPIC_CC__"]
    else:
        # xc8: the framework package's default shape already IS the XC8
        # one (include/target, hal_sources); no path remapping needed.
        includes = [join(fw_dir, d) for d in manifest["family_includes"]]
        defines = ["-DPIC%s" % device]
        # Per-device sources (e.g. pic16f87xa_psp.c on the 874A/877A only):
        # the real vector table references every peripheral unconditionally
        # (EPIC_WEAK is a no-op there), so omitting one is a link error, not
        # a latent gap like on epic-cc's slimmer vector file. `after`
        # positions a source right after a specific hal_source, since XC8's
        # link order affects psect layout; the shipped framework package
        # does not carry `after` yet (epic-hal#164), so this currently
        # always falls through to appending at the end.
        applicable = [
            c for c in manifest.get("conditional_sources", [])
            if device in c["variants"]
        ]
        matched = [False] * len(applicable)
        sources = []
        for hal_src in manifest["hal_sources"]:
            sources.append(join(fw_dir, hal_src))
            for i, c in enumerate(applicable):
                if c.get("after") == hal_src:
                    sources.append(join(fw_dir, c["path"]))
                    matched[i] = True
        for i, c in enumerate(applicable):
            if c.get("after") is None:
                sources.append(join(fw_dir, c["path"]))
            elif not matched[i]:
                # A stale or mistyped `after` must not silently drop the
                # source from the build: it needs the specific hal_source
                # it names to exist, and this family's list has changed
                # out from under it.
                sys.stderr.write(
                    "Error: conditional source %s has after=%r, which "
                    "matches no hal_source for %s\n" % (c["path"], c["after"], slug)
                )
                env.Exit(1)
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
    # A module's own sources can repeat a file the family's base hal_sources
    # already carries (epic-common/src/core/epic_harness_target.c, via the
    # "common" module): harmless as a second argument to epic-cc's single
    # invocation, but a hard SCons error as two per-object Command nodes
    # targeting the same object path under xc8. Dedup once, order-preserved.
    sources = list(dict.fromkeys(sources))
    return sources, includes, defines


fw_sources, fw_includes, fw_defines = _framework(env, mcu, toolchain)

# Real source paths, not variant-dir copies: both toolchains read the
# files directly, whether whole-program (epic-cc) or per-file (xc8). The
# project lib/ dir joins the sources either way, so project libraries are
# always part of the same build, never a separate link step of their own.
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


# XC8's flag set, including the whole -Wno-* list, is ported verbatim from
# epic-hal's own build driver (scripts/epic_build.py), which triaged every
# one of these against real XC8 output; re-deriving it here would risk
# losing that triage. See that file for what each suppressed warning is.
_XC8_CFLAGS = [
    "-O2", "-std=c99", "-Wall", "-Wextra",
    "-Wno-520", "-Wno-2053", "-Wno-759", "-Wno-1516",
    "-Wno-1311", "-Wno-1262", "-Wno-1510", "-Wno-2098",
    "-Wno-1498",
    "-Wno-unused-function", "-Wno-unused-variable",
    "-Wno-unused-parameter", "-Wno-sign-conversion",
    "-Wno-implicit-int-conversion",
]


def _xc8_cflags():
    flags = []
    if xc8_dfp_dir:
        flags.append("-mdfp=%s" % xc8_dfp_dir)
    flags.append("-mcpu=%s" % bare_mcu.lower())
    flags += _XC8_CFLAGS
    for d in include_dirs:
        flags += ["-I", d]
    flags += defines
    return flags


def _xc8_obj_name(src_path):
    # A hash-derived name, not a flattened path: manual path escaping
    # turns out fragile (two prior schemes each had a real collision
    # case), so only the basename is kept for readability and a hash of
    # the full path guarantees two distinct sources never collide.
    digest = hashlib.sha1(src_path.encode("utf-8")).hexdigest()[:16]
    return "%s.%s.p1" % (os.path.basename(src_path), digest)


def _xc8_compile_action(src_path, cflags):
    # A closure factory, not a loop-body def: capturing src_path (and the
    # shared cflags, computed once by the caller rather than per file) as
    # default arguments is what keeps each per-file SCons action bound to
    # its own source instead of all of them silently compiling the last
    # one.
    def _compile(target, source, env, src_path=src_path, cflags=cflags):
        cmd = [xc8cc] + cflags + ["-c", src_path, "-o", str(target[0])]
        print("xc8-cc %s" % " ".join(cmd[1:]))
        return subprocess.call(cmd)
    return _compile


def _xc8_link(target, source, env):
    # Link with device + optimization only: the link inputs are prebuilt
    # objects, so -std/-Wall/-D/-I are void there, and XC8 forwards extra
    # flags into its own runtime-support compile, which has miscompiled on
    # at least one device with them present (epic-hal#136). -O2 stays: it
    # still governs support codegen.
    linkflags = []
    if xc8_dfp_dir:
        linkflags.append("-mdfp=%s" % xc8_dfp_dir)
    linkflags += ["-mcpu=%s" % bare_mcu.lower(), "-O2"]
    cmd = [xc8cc] + linkflags + [str(s) for s in source] + ["-o", str(target[0]), "-ginhx32"]
    print("xc8-cc %s" % " ".join(cmd[1:]))
    return subprocess.call(cmd)


if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

xc8_objs = []
if toolchain == "xc8":
    # One SCons node per object, not one Command looping over every
    # source: lets SCons parallelize (-j) and rebuild only the objects
    # whose own source actually changed, the ordinary compile-then-link
    # shape XC8 has, unlike epic-cc's single whole-program invocation.
    objdir = env.subst("$BUILD_DIR")
    xc8_cflags = _xc8_cflags()
    for src in sources:
        src_path = str(src)
        obj_path = join(objdir, _xc8_obj_name(src_path))
        xc8_objs.append(env.Command(obj_path, src, _xc8_compile_action(src_path, xc8_cflags)))
    firmware = env.Command(join("$BUILD_DIR", "${PROGNAME}.hex"), xc8_objs, _xc8_link)
else:
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
if toolchain == "xc8":
    # A header edit must invalidate every object node, not just the final
    # link (which never re-reads a header at all, so depending firmware on
    # header_deps directly would be redundant with this): a stale .p1
    # would otherwise silently relink unchanged.
    for obj in xc8_objs:
        env.Depends(obj, header_deps)
else:
    env.Depends(firmware, header_deps)

AlwaysBuild(env.Alias("buildprog", firmware, firmware))

# Upload. `minipro` drives a TL866A / TL866II Plus universal programmer
# (docs/platform-decisions.md): fully independent of Microchip (XGecu
# hardware, GPL tool), unlike pk2cmd/ipecmd, which is why it is the first
# protocol wired here rather than either of those. Neither minipro nor
# pk2cmd has a Debian/Ubuntu package, and vendoring our own prebuilt
# binaries is a distribution project on the scale of epic-cc's
# docs/30-distribution-design.md, so v1 finds a binary the user already
# built, on PATH or via EPIC8_MINIPRO_PATH, rather than shipping one.
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


def _upload_pk2cmd(source):
    binary = os.environ.get("EPIC8_PK2CMD_PATH") or shutil.which("pk2cmd")
    if not binary:
        sys.stderr.write(
            "Error: pk2cmd not found on PATH. Build it from "
            "https://github.com/cjacker/pk2cmd-minus (no Debian/Ubuntu "
            "package exists) and either put it on PATH or point "
            "EPIC8_PK2CMD_PATH at the binary. See "
            "docs/getting-started.md#upload.\n"
        )
        return 1
    device = board.get("upload.pk2cmd_device", "")
    if not device:
        sys.stderr.write(
            "Error: board %s has no upload.pk2cmd_device\n" % board.id
        )
        return 1
    # `pk2cmd -P<part> -F <hex> -M -E` programs the whole chip (program +
    # config, and erase first), the same one-shot shape minipro's `-w` uses.
    cmd = [binary, "-P" + device, "-F", str(source[0]), "-M", "-E"]
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
