from __future__ import annotations

import stat
import textwrap
from pathlib import Path

from osai.spec import OSSpec


def write_kernel_recipe(project: Path, spec: OSSpec) -> None:
    script = project / "kernel/build-branded-kernel.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/sh
            set -eu
            ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
            WORK="$ROOT/kernel/work"
            OUT="$ROOT/config/packages.chroot"
            mkdir -p "$WORK" "$OUT"

            command -v make >/dev/null 2>&1 || {{ echo 'make is required' >&2; exit 2; }}
            command -v dpkg-buildpackage >/dev/null 2>&1 || {{ echo 'dpkg-dev is required' >&2; exit 2; }}

            KVER=$(uname -r)
            CFG="/boot/config-$KVER"
            [ -f "$CFG" ] || {{ echo "missing host kernel config: $CFG" >&2; exit 3; }}

            cd "$WORK"
            if [ ! -d linux-source ]; then
              apt-get source linux
              SRC=$(find . -maxdepth 1 -type d -name 'linux-*' | head -n1)
              [ -n "$SRC" ] || {{ echo 'linux source was not downloaded' >&2; exit 4; }}
              mv "$SRC" linux-source
            fi

            cd linux-source
            cp "$CFG" .config
            scripts/config --set-str LOCALVERSION '{spec.kernel.local_version}'
            scripts/config --enable LOCALVERSION_AUTO
            make olddefconfig
            make -j"$(nproc)" bindeb-pkg LOCALVERSION='{spec.kernel.local_version}'

            find .. -maxdepth 1 -type f -name 'linux-image-*.deb' -exec cp {{}} "$OUT/" \;
            find .. -maxdepth 1 -type f -name 'linux-headers-*.deb' -exec cp {{}} "$OUT/" \;
            echo "Branded kernel packages copied to $OUT"
            """
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
