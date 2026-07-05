"""`trcompile` console-script entry point.

Backends (LLM invocation options): claude-code (default, tried first), api
(Anthropic SDK), cursor, mock (offline, CI/tests). See tec/compile/backends.py.
The gates are identical for every backend.
"""

from __future__ import annotations

import argparse
import os
import sys

from tec.compile.backends import (
    BACKENDS,
    BackendUnavailable,
    available_backends,
    resolve_backend,
)
from tec.compile.compiler import CompileError, compile_trial


def _default_backend() -> str:
    return os.environ.get("TRCOMPILE_BACKEND", "auto")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trcompile",
        description="Compile verbatim eligibility prose into a committed OHDSI cohort.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    build = sub.add_parser("build", help="run the compile loop and write the artifact")
    build.add_argument("--trial", default="NCT03667300")
    build.add_argument(
        "--backend", default=_default_backend(), choices=["auto", *BACKENDS],
        help="LLM invocation option (default: auto -> claude-code, then api, then cursor). "
             "Env: TRCOMPILE_BACKEND.",
    )
    build.add_argument("--model", default=None, help="override the backend's model id")
    build.add_argument("--out", default=None, help="output dir (default: compiled/<trial>/)")

    sub.add_parser("backends", help="show which LLM backends are available here")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.cmd == "backends":
        for name, ok in available_backends().items():
            print(f"  {'available' if ok else 'unavailable':<12} {name}")
        return 0

    if args.cmd == "build":
        try:
            client = resolve_backend(args.backend, model=args.model)
        except (BackendUnavailable, ValueError) as e:
            sys.stderr.write(f"trcompile: {e}\n")
            return 3
        desc = getattr(client, "descriptor", lambda: {"backend": args.backend})()
        try:
            result = compile_trial(args.trial, client, out_dir=args.out)
        except BackendUnavailable as e:
            sys.stderr.write(f"trcompile: {e}\n")
            return 3
        except CompileError as e:
            sys.stderr.write(f"trcompile: {e}\n")
            return 1
        print(f"trcompile: compiled {args.trial} in {result.attempts} attempt(s) "
              f"[{desc}] -> {result.out_dir}")
        print("  wrote: " + ", ".join(result.written))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
