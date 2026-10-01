from __future__ import annotations

import re
from pathlib import Path

from osai.design.analyzer import analyze_references
from osai.spec import KernelSpec, OSSpec, PackageSpec, ThemeSpec


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "osai-os"


def _contains(prompt: str, *terms: str) -> bool:
    p = prompt.lower()
    return any(term.lower() in p for term in terms)


def build_spec(name: str, prompt: str, references: list[Path]) -> OSSpec:
    visuals = analyze_references(references)

    desktop = "kde"
    if _contains(prompt, "gnome"):
        desktop = "gnome"
    elif _contains(prompt, "xfce"):
        desktop = "xfce"
    elif _contains(prompt, "cinnamon"):
        desktop = "cinnamon"
    elif _contains(prompt, "lxqt"):
        desktop = "lxqt"

    gaming = _contains(prompt, "game", "gaming", "steam", "proton", "wine", "jogos")
    development = _contains(prompt, "program", "developer", "desenvolvimento", "coding", "git")
    mode = "light" if _contains(prompt, "light mode", "modo claro") else "dark"

    packages: list[str] = []
    if gaming:
        packages += ["steam-installer", "wine", "winetricks", "gamemode", "mangohud"]
    if development:
        packages += ["git", "build-essential", "python3", "python3-venv", "curl"]
    if _contains(prompt, "bluetooth"):
        packages += ["bluetooth", "bluez"]
    if _contains(prompt, "vulkan") or gaming:
        packages += ["mesa-vulkan-drivers", "vulkan-tools"]

    slug = _slugify(name)
    theme = ThemeSpec(
        mode=mode,
        accent=visuals.accent,
        background=visuals.background,
        foreground=visuals.foreground,
        radius_px=visuals.radius_px,
        blur=visuals.blur,
        reference_images=[str(p) for p in references],
    )

    return OSSpec(
        name=name,
        slug=slug,
        hostname=slug[:63],
        prompt=prompt,
        theme=theme,
        kernel=KernelSpec(display_name=f"{name} Kernel", local_version=f"-{slug}"),
        software=PackageSpec(
            desktop=desktop,
            browser="chromium",
            packages=sorted(set(packages)),
            gaming=gaming,
            development=development,
            media=True,
        ),
        features=[
            "hybrid-uefi-bios-iso",
            "hardware-firmware-preservation",
            "syntax-validation-before-build",
            "source-project-export",
        ],
    )
