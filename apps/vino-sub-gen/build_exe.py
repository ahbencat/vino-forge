#!/usr/bin/env python3
"""Package the GUI into a Windows exe (onedir).

Usage (from this directory):
    python build_exe.py [extra PyInstaller args...]

Why this wrapper exists: the environment runs CPython 3.10.0, whose `dis`
module raises `IndexError` on some large code objects (fixed in 3.10.1,
CPython bpo-45745). `sympy.matrices.matrixbase` — pulled in transitively by
optimum-intel — is one such module, and PyInstaller's static analysis
scans bytecode of every bundled module, so a plain build crashes.

The interpreter itself executes that bytecode fine; only the
disassembler chokes. We therefore make the instruction stream best-effort
during analysis (partial scans still yield enough hidden-import
information, and the spec additionally collects all sympy submodules
explicitly). The patch only affects this build process — the frozen app
runs the same bytecode unaffected.
"""

import dis
import sys
from pathlib import Path

_orig_get_instructions = dis.get_instructions


def _tolerant_instructions(*args, **kwargs):
    """Yield instructions; stop early (instead of raising) on the 3.10.0 dis bug."""
    try:
        yield from _orig_get_instructions(*args, **kwargs)
    except IndexError:
        return


def main():
    dis.get_instructions = _tolerant_instructions

    from PyInstaller.__main__ import run

    spec = Path(__file__).resolve().parent / "vino-sub-gen.spec"
    argv = [str(spec), "--noconfirm", "--distpath", "dist", "--workpath", "build", *sys.argv[1:]]
    run(argv)


if __name__ == "__main__":
    main()
