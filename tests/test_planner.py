from pathlib import Path

from osai.ai.planner import build_spec


def test_planner_detects_gaming_features() -> None:
    spec = build_spec(
        "LunnaOS",
        "KDE dark gaming OS with Steam, Wine, Vulkan and development tools",
        [],
    )
    assert spec.software.desktop == "kde"
    assert spec.software.gaming is True
    assert "steam-installer" in spec.software.packages
    assert "mesa-vulkan-drivers" in spec.software.packages
    assert spec.kernel.preserve_modules is True


def test_slug_is_safe() -> None:
    spec = build_spec("Meu Sistema 1!", "desktop simples", [])
    assert spec.slug == "meu-sistema-1"
    assert spec.hostname == "meu-sistema-1"
