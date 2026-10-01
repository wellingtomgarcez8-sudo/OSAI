from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat


@dataclass(slots=True)
class VisualProfile:
    accent: str = "#7c3aed"
    background: str = "#111827"
    foreground: str = "#f8fafc"
    radius_px: int = 14
    blur: bool = True


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def analyze_references(paths: list[Path]) -> VisualProfile:
    if not paths:
        return VisualProfile()

    means: list[tuple[int, int, int]] = []
    saturated: list[tuple[int, int, int]] = []

    for path in paths:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((512, 512))
            stat = ImageStat.Stat(image)
            mean = tuple(int(v) for v in stat.mean[:3])
            means.append(mean)

            quantized = image.quantize(colors=12).convert("RGB")
            palette = quantized.getcolors(maxcolors=quantized.width * quantized.height) or []
            for count, color in sorted(palette, reverse=True)[:12]:
                hi, lo = max(color), min(color)
                if hi - lo >= 35 and 35 <= _luma(color) <= 220:
                    saturated.extend([color] * max(1, count // 500))

    avg = tuple(sum(c[i] for c in means) // len(means) for i in range(3))
    background = avg
    foreground = (248, 250, 252) if _luma(background) < 145 else (15, 23, 42)

    if saturated:
        accent = tuple(sum(c[i] for c in saturated) // len(saturated) for i in range(3))
    else:
        accent = (124, 58, 237)

    return VisualProfile(
        accent=_hex(accent),
        background=_hex(background),
        foreground=_hex(foreground),
        radius_px=16,
        blur=True,
    )
