#!/bin/sh
set -eu

sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip \
  live-build debootstrap xorriso squashfs-tools \
  grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
  qemu-system-x86 ovmf git

echo "OSAI build dependencies installed."
