from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Desktop = Literal["kde", "gnome", "xfce", "cinnamon", "lxqt"]
BaseDistro = Literal["debian"]


class ThemeSpec(BaseModel):
    mode: Literal["dark", "light", "auto"] = "dark"
    accent: str = "#7c3aed"
    background: str = "#111827"
    foreground: str = "#f8fafc"
    radius_px: int = Field(default=14, ge=0, le=48)
    blur: bool = True
    reference_images: list[str] = Field(default_factory=list)

    @field_validator("accent", "background", "foreground")
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must be #RRGGBB")
        int(value[1:], 16)
        return value.lower()


class KernelSpec(BaseModel):
    display_name: str = "OSAI Kernel"
    local_version: str = "-osai"
    preserve_distro_config: bool = True
    preserve_modules: bool = True
    preserve_firmware: bool = True


class PackageSpec(BaseModel):
    desktop: Desktop = "kde"
    browser: str = "chromium"
    packages: list[str] = Field(default_factory=list)
    gaming: bool = False
    development: bool = False
    media: bool = True


class OSSpec(BaseModel):
    schema_version: int = 1
    name: str
    slug: str
    version: str = "0.1.0"
    architecture: Literal["amd64"] = "amd64"
    base: BaseDistro = "debian"
    debian_release: str = "trixie"
    locale: str = "pt_BR.UTF-8"
    timezone: str = "America/Sao_Paulo"
    hostname: str
    username: str = "user"
    prompt: str
    theme: ThemeSpec = Field(default_factory=ThemeSpec)
    kernel: KernelSpec = Field(default_factory=KernelSpec)
    software: PackageSpec = Field(default_factory=PackageSpec)
    features: list[str] = Field(default_factory=list)

    @field_validator("slug", "hostname")
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
        lowered = value.lower()
        if not lowered or any(ch not in allowed for ch in lowered):
            raise ValueError("identifier may contain only a-z, 0-9 and -")
        return lowered

    def dump_yaml(self, path: Path) -> None:
        import yaml

        path.write_text(
            yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
