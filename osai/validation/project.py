from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from osai.spec import OSSpec


FORBIDDEN_SNIPPETS = (
    "rm -rf /",
    "mkfs.",
    "> /dev/sd",
    "dd if=/dev/zero of=/dev/",
)


@dataclass(slots=True)
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)


def _shell_files(project: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in project.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".sh" or path.name.endswith(".hook.chroot") or "auto" in path.parts:
            candidates.append(path)
    return candidates


def validate_project(project: Path) -> ValidationResult:
    result = ValidationResult()
    spec_path = project / "osai.yaml"
    if not spec_path.exists():
        result.fail("missing osai.yaml")
        return result

    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        OSSpec.model_validate(raw)
    except Exception as exc:  # pydantic/yaml report exact field context
        result.fail(f"invalid osai.yaml: {exc}")

    required = [
        project / "auto/config",
        project / "config/package-lists/osai.list.chroot",
        project / "build.sh",
    ]
    for path in required:
        if not path.is_file():
            result.fail(f"missing required file: {path.relative_to(project)}")

    shell = shutil.which("sh")
    for path in _shell_files(project):
        text = path.read_text(encoding="utf-8", errors="replace")
        for bad in FORBIDDEN_SNIPPETS:
            if bad in text:
                result.fail(f"unsafe generated command in {path.relative_to(project)}: {bad!r}")
        if shell:
            proc = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True)
            if proc.returncode:
                result.fail(
                    f"shell syntax error in {path.relative_to(project)}: {proc.stderr.strip()}"
                )

    packages = project / "config/package-lists/osai.list.chroot"
    if packages.exists():
        lines = [x.strip() for x in packages.read_text(encoding="utf-8").splitlines() if x.strip()]
        for essential in ("linux-image-amd64", "network-manager", "firmware-linux"):
            if essential not in lines:
                result.fail(f"hardware-preservation package missing: {essential}")

    if not shutil.which("lb"):
        result.warnings.append("live-build is not installed on this host; generation is valid but ISO build cannot run yet")

    return result
