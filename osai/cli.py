from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from osai.ai.planner import build_spec
from osai.generator.compiler import compile_project
from osai.validation.project import validate_project


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    raise SystemExit("provide --prompt or --prompt-file")


def cmd_create(args: argparse.Namespace) -> int:
    refs = [Path(x).resolve() for x in args.reference]
    missing = [str(x) for x in refs if not x.is_file()]
    if missing:
        raise SystemExit("reference image(s) not found: " + ", ".join(missing))
    spec = build_spec(args.name, _read_prompt(args), refs)
    project = compile_project(spec, Path(args.out).resolve())
    result = validate_project(project)
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if not result.ok:
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(project)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    result = validate_project(Path(args.project).resolve())
    for warning in result.warnings:
        print(f"warning: {warning}")
    for error in result.errors:
        print(f"error: {error}")
    if result.ok:
        print("OSAI validation passed.")
        return 0
    return 1


def cmd_build(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    result = validate_project(project)
    if not result.ok:
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    return subprocess.call([str(project / "build.sh")], cwd=project)


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("install web support with: pip install -e '.[web]'") from exc
    uvicorn.run("osai.web.app:app", host=args.host, port=args.port, reload=False)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="osai", description="Local Linux OS generator")
    sub = p.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="generate a Linux OS project")
    create.add_argument("--name", required=True)
    group = create.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt")
    group.add_argument("--prompt-file")
    create.add_argument("--reference", action="append", default=[])
    create.add_argument("--out", default="./work")
    create.set_defaults(func=cmd_create)

    validate = sub.add_parser("validate", help="validate a generated project")
    validate.add_argument("project")
    validate.set_defaults(func=cmd_validate)

    build = sub.add_parser("build", help="validate and build an ISO")
    build.add_argument("project")
    build.set_defaults(func=cmd_build)

    serve = sub.add_parser("serve", help="start local OSAI web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=7860)
    serve.set_defaults(func=cmd_serve)
    return p


def main() -> None:
    args = parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
