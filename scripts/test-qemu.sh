#!/usr/bin/env bash
# 빌드한 ISO 를 QEMU 로 부팅해 봅니다 (저사양 재현: 기본 2 CPU / 2GB RAM).
#   ./scripts/test-qemu.sh [iso] [--uefi] [--ram MB] [--cpus N] [--disk]
# shellcheck disable=SC2054  # qemu 옵션 값 안의 쉼표는 의도된 것
set -euo pipefail
cd "$(dirname "$0")/.."

ISO=""
UEFI=0
RAM=2048
CPUS=2
DISK=0
while [ $# -gt 0 ]; do
    case "$1" in
        --uefi) UEFI=1 ;;
        --ram) RAM="$2"; shift ;;
        --cpus) CPUS="$2"; shift ;;
        --disk) DISK=1 ;;
        *.iso) ISO="$1" ;;
        *) echo "알 수 없는 옵션: $1" >&2; exit 1 ;;
    esac
    shift
done
[ -n "$ISO" ] || ISO=$(find . -maxdepth 1 -name "*.iso" -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -1 | cut -d" " -f2-)
if [ -z "$ISO" ] || [ ! -f "$ISO" ]; then
    echo "ISO 파일이 없습니다. 먼저 빌드하세요." >&2
    exit 1
fi

command -v qemu-system-x86_64 >/dev/null || { echo "qemu-system-x86 를 설치하세요." >&2; exit 1; }

args=( -m "$RAM" -smp "$CPUS" -cdrom "$ISO" -boot d
       -device virtio-vga -display gtk,gl=off
       -device virtio-net-pci,netdev=n0 -netdev user,id=n0
       -audiodev pa,id=snd0 -device intel-hda -device hda-output,audiodev=snd0
       -usb -device usb-tablet )
[ -w /dev/kvm ] && args+=( -enable-kvm -cpu host )

if [ "$UEFI" = 1 ]; then
    for fw in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/edk2/x64/OVMF_CODE.4m.fd; do
        [ -f "$fw" ] && { args+=( -bios "$fw" ); break; }
    done
fi

if [ "$DISK" = 1 ]; then
    mkdir -p .qemu
    [ -f .qemu/disk.qcow2 ] || qemu-img create -f qcow2 .qemu/disk.qcow2 32G >/dev/null
    args+=( -drive file=.qemu/disk.qcow2,if=virtio,format=qcow2 )
fi

echo "qemu-system-x86_64 ${args[*]}"
exec qemu-system-x86_64 "${args[@]}"
