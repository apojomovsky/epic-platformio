"""Build script for platform-epic8.

epic-cc is a whole-program compiler (epic-cc docs/31 D-7): every C source
goes into one invocation, so there are no per-object compile rules and no
linker. This script collects the project sources and hands them to epic-cc
in a single command.
"""

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
env.Depends(firmware, header_deps)

AlwaysBuild(env.Alias("buildprog", firmware, firmware))

# Upload is not supported in v1: the HEX is the deliverable. Flashing is
# left to the user's own programmer (pk2cmd, ipecmd, a bootloader), which
# keeps the platform free of Microchip downloads (docs/31 D-5).
def _upload_not_supported(target, source, env):
    sys.stderr.write(
        "Error: upload is not supported by platform-epic8 in v1; the HEX "
        "at %s is the deliverable. Flash it with your own programmer.\n"
        % str(firmware[0])
    )
    env.Exit(1)


AlwaysBuild(env.Alias("upload", firmware, _upload_not_supported))
AlwaysBuild(env.Alias("program", firmware, _upload_not_supported))

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
