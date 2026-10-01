from __future__ import annotations

import json
import shutil
import stat
import textwrap
from pathlib import Path

from osai.generator.kernel_recipe import write_kernel_recipe
from osai.spec import OSSpec


DESKTOP_PACKAGES = {
    "kde": ["kde-standard", "sddm"],
    "gnome": ["gnome-core", "gdm3"],
    "xfce": ["xfce4", "lightdm"],
    "cinnamon": ["cinnamon-core", "lightdm"],
    "lxqt": ["lxqt", "sddm"],
}

BASE_PACKAGES = [
    "linux-image-amd64",
    "live-boot",
    "systemd-sysv",
    "network-manager",
    "wpasupplicant",
    "wireless-regdb",
    "firmware-linux",
    "firmware-linux-free",
    "firmware-misc-nonfree",
    "firmware-iwlwifi",
    "firmware-realtek",
    "firmware-atheros",
    "firmware-amd-graphics",
    "intel-microcode",
    "amd64-microcode",
    "mesa-utils",
    "mesa-vulkan-drivers",
    "pipewire",
    "wireplumber",
    "bluez",
    "bluez-tools",
    "xserver-xorg-input-libinput",
    "sudo",
    "curl",
    "ca-certificates",
    "locales",
]


def _write(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _desktop_theme(spec: OSSpec) -> str:
    t = spec.theme
    return textwrap.dedent(
        f"""\
        [OSAI Theme]
        name={spec.name}
        mode={t.mode}
        accent={t.accent}
        background={t.background}
        foreground={t.foreground}
        radius={t.radius_px}
        blur={'true' if t.blur else 'false'}
        """
    )


def compile_project(spec: OSSpec, destination: Path) -> Path:
    project = destination / spec.name
    if project.exists():
        raise FileExistsError(f"destination already exists: {project}")
    project.mkdir(parents=True)

    spec.dump_yaml(project / "osai.yaml")
    (project / "references").mkdir()
    for raw in spec.theme.reference_images:
        src = Path(raw)
        if src.exists() and src.is_file():
            shutil.copy2(src, project / "references" / src.name)

    package_list = sorted(
        set(
            BASE_PACKAGES
            + DESKTOP_PACKAGES[spec.software.desktop]
            + [spec.software.browser]
            + spec.software.packages
        )
    )
    _write(project / "config/package-lists/osai.list.chroot", "\n".join(package_list) + "\n")

    _write(
        project / "auto/config",
        textwrap.dedent(
            f"""\
            #!/bin/sh
            set -eu
            lb config noauto \\
              --mode debian \\
              --distribution {spec.debian_release} \\
              --architectures {spec.architecture} \\
              --binary-images iso-hybrid \\
              --archive-areas "main contrib non-free non-free-firmware" \\
              --debian-installer live \\
              --bootappend-live "boot=live components hostname={spec.hostname} username={spec.username} locales={spec.locale}" \\
              "$@"
            """
        ),
        executable=True,
    )

    _write(
        project / "config/includes.chroot/etc/os-release",
        textwrap.dedent(
            f"""\
            PRETTY_NAME="{spec.name} {spec.version}"
            NAME="{spec.name}"
            VERSION_ID="{spec.version}"
            ID={spec.slug}
            ID_LIKE=debian
            HOME_URL="https://github.com/"
            SUPPORT_URL="https://github.com/"
            BUG_REPORT_URL="https://github.com/"
            """
        ),
    )
    _write(project / "config/includes.chroot/etc/osai/theme.conf", _desktop_theme(spec))
    _write(
        project / "config/includes.chroot/etc/osai/spec.json",
        json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
    )

    _write(
        project / "config/hooks/live/020-osai-kernel-branding.hook.chroot",
        textwrap.dedent(
            f"""\
            #!/bin/sh
            set -eu
            mkdir -p /etc/osai
            printf '%s\n' '{spec.kernel.display_name}' > /etc/osai/kernel-display-name
            printf '%s\n' '{spec.kernel.local_version}' > /etc/osai/kernel-local-version
            update-initramfs -u -k all || true
            """
        ),
        executable=True,
    )

    _write(
        project / "config/hooks/live/030-osai-user.hook.chroot",
        textwrap.dedent(
            f"""\
            #!/bin/sh
            set -eu
            if ! id {spec.username} >/dev/null 2>&1; then
              useradd -m -s /bin/bash -G sudo,audio,video,plugdev,netdev {spec.username}
            fi
            printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' '{spec.username}' >/etc/sudoers.d/90-osai-live
            chmod 0440 /etc/sudoers.d/90-osai-live
            """
        ),
        executable=True,
    )

    write_kernel_recipe(project, spec)

    _write(
        project / "build.sh",
        textwrap.dedent(
            """\
            #!/bin/sh
            set -eu
            ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
            cd "$ROOT"
            command -v lb >/dev/null 2>&1 || { echo 'live-build (lb) is required' >&2; exit 2; }
            ./validate.sh
            if [ "${OSAI_BUILD_KERNEL:-0}" = "1" ]; then
              ./kernel/build-branded-kernel.sh
            fi
            sudo lb clean --purge || true
            sudo lb config
            sudo lb build
            mkdir -p dist
            ISO=$(find . -maxdepth 1 -type f \( -name '*.hybrid.iso' -o -name '*.iso' \) -print | head -n1 || true)
            [ -n "$ISO" ] || { echo 'ISO was not produced' >&2; exit 3; }
            cp "$ISO" "dist/osai.iso"
            sha256sum "dist/osai.iso" > "dist/osai.iso.sha256"
            echo "ISO: $ROOT/dist/osai.iso"
            """
        ),
        executable=True,
    )

    _write(
        project / "validate.sh",
        textwrap.dedent(
            """\
            #!/bin/sh
            set -eu
            ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
            find "$ROOT" -type f \( -name '*.sh' -o -name '*.hook.chroot' -o -path '*/auto/*' \) -print |
              while IFS= read -r f; do sh -n "$f"; done
            test -s "$ROOT/config/package-lists/osai.list.chroot"
            test -s "$ROOT/osai.yaml"
            echo 'Project validation passed.'
            """
        ),
        executable=True,
    )

    _write(
        project / ".gitignore",
        ".build/\n.cache/\nbinary*\nchroot*\nconfig/bootstrap\nconfig/chroot\nconfig/common\nconfig/source\n*.iso\ndist/*.iso\nkernel/work/\n",
    )

    _write(
        project / "SOURCE_INFO.txt",
        f"Generated by OSAI\nName: {spec.name}\nVersion: {spec.version}\nBase: Debian {spec.debian_release}\n",
    )
    return project
