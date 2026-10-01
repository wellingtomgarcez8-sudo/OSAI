# OSAI — Operating System Artificial Intelligence

OSAI is a local-first operating-system generator. It accepts a natural-language brief plus optional reference images and produces a reproducible Linux OS source tree and bootable ISO build recipe.

> Status: early developer preview. OSAI does **not** call OpenAI, Anthropic, Google, or any other hosted AI API. The repository contains its own orchestration, validation, design extraction, OS templates, and an optional trainable local Transformer model. A freshly cloned repository does not magically contain a fully-trained foundation model; model weights must be trained locally or supplied as local files.

## Goals

- Prompt + reference images -> structured OS specification.
- Generate a complete Debian-based live system project.
- Brand the kernel as an OSAI-generated kernel while preserving Linux driver support and the distro kernel configuration.
- Preserve firmware, Mesa, Vulkan, Wi-Fi, Bluetooth, audio, touchpad, keyboard, storage and common GPU packages whenever the selected base supports them.
- Generate desktop theme, boot splash, login branding, default applications and package lists.
- Validate shell, YAML, Python, desktop entries and generated project structure before a build.
- Build a bootable hybrid ISO for UEFI/BIOS using `live-build`.
- Keep every generated file in a project workspace so the user receives the source as well as the ISO.
- Work offline after dependencies/base packages/model weights are locally available.

## What “own AI” means here

OSAI has no dependency on API tokens from another AI. The runtime is split into:

1. **OS planner** — deterministic structured planner that works immediately.
2. **Local model runtime** — a decoder-only Transformer implemented in this repository and loaded from local weights when available.
3. **Tool/validator loop** — OSAI does not trust generated code blindly; it parses, lints, validates and can revise generation plans before allowing an ISO build.
4. **OS compiler** — converts the specification into an auditable Linux live-build source tree.

The model training code is included so OSAI can become a genuinely independent learned model instead of secretly proxying another service.

## Quick start

Requirements: Linux host, Python 3.11+, root/sudo for ISO creation, `live-build`, `debootstrap`, `xorriso`, `squashfs-tools`, `grub-pc-bin`, `grub-efi-amd64-bin`, `mtools`, `dosfstools`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Generate a project (does not require model weights)
osai create --name LunnaOS --prompt "A smooth dark gaming OS with purple accents, KDE Plasma, Steam, Wine and Chromium" --out ./work

# Validate it
osai validate ./work/LunnaOS

# Build the ISO (Linux host, sudo required)
osai build ./work/LunnaOS
```

Reference images can be passed repeatedly:

```bash
osai create --name LunnaOS \
  --prompt-file brief.txt \
  --reference ./refs/desktop.png \
  --reference ./refs/login.png \
  --out ./work
```

The finished ISO is written to `PROJECT/dist/` and all buildable source remains in the project directory.

## Local web UI

```bash
pip install -e '.[web]'
osai serve --host 127.0.0.1 --port 7860
```

Open `http://127.0.0.1:7860` and submit the OS name, prompt and reference images.

## Kernel branding without losing drivers

OSAI deliberately does not replace Linux with an empty custom kernel. Instead it keeps the selected distro kernel source/configuration and driver ecosystem, applies an OSAI local version/branding, and emits build hooks that install the branded kernel package into the live image. That preserves the hardware-enablement work already present in Linux while still giving the generated OS its own kernel identity in `uname -r`, boot entries and package metadata.

## Repository map

```text
osai/
  ai/          local model, planner and prompt understanding
  design/      reference-image theme extraction
  generator/   Linux project compiler and templates
  validation/  syntax and project validators
  web/         local HTTP/UI service
scripts/       host setup and convenience scripts
tests/         unit tests
```

## Security model

Generated scripts are treated as untrusted until validation. Builds run only after validation succeeds. OSAI rejects obvious destructive host commands in generated hooks, keeps generated work inside its project directory, and prints every privileged command before execution.

## License

MIT for OSAI's own source code. Generated distributions remain subject to the licenses of Linux, Debian packages, firmware, themes, fonts and applications included in them.