"""Declared framework script for `framework = epichal`.

The build itself lives in builder/main.py, which already wires the HAL
into both toolchains and branches on whether the project sets the
framework. This file exists so the platform manifest's script entry
resolves per PlatformIO's convention; if it is ever SConscripted it
must stay a no-op, or the whole build would run twice.
"""
