#!/usr/bin/env bash
# ISO 자동 부팅 테스트 (CI 용). QEMU 로 라이브 세션을 부팅해서
#   - BIOS + 직접 커널 부팅: 시리얼 콘솔 로그, 게스트 안에서 자원/서비스 측정, 화면 스크린샷
#   - UEFI (OVMF, 가능하면 Secure Boot 키 포함): ISO 부트로더 경로 확인, 스크린샷
# 를 <outdir> 에 남깁니다. root 권한(mount) 이 필요합니다.
#   sudo ./scripts/boot-test.sh <iso> <outdir> [wait-seconds]
# shellcheck disable=SC2054  # qemu 옵션 값 안의 쉼표는 의도된 것
set -uo pipefail
ISO=${1:?iso}; OUT=${2:?outdir}; WAIT=${3:-150}
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd); ISO=$(cd "$(dirname "$ISO")" && pwd)/$(basename "$ISO")
HERE=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
SUMMARY="$OUT/summary.txt"; : > "$SUMMARY"
note() { echo "$*" | tee -a "$SUMMARY"; }

KVM=()
if [ -w /dev/kvm ]; then KVM=(-enable-kvm -cpu host); note "kvm: yes"; else note "kvm: no (software emulation, 느림)"; WAIT=$((WAIT * 4)); fi

mon() {  # QEMU 모니터에 명령 하나 전송
    python3 - "$1" "$2" <<'PY'
import socket, sys, time
s = socket.socket(socket.AF_UNIX); s.settimeout(3); s.connect(sys.argv[1])
try: s.recv(65536)
except Exception: pass
s.sendall((sys.argv[2] + "\n").encode()); time.sleep(1)
try: s.recv(65536)
except Exception: pass
PY
}
shot() {  # 스크린샷 (ppm -> png)
    mon "$1" "screendump $TMP/shot.ppm"; sleep 1
    if command -v convert >/dev/null 2>&1; then convert "$TMP/shot.ppm" "$2" 2>/dev/null || cp "$TMP/shot.ppm" "${2%.png}.ppm"; else cp "$TMP/shot.ppm" "${2%.png}.ppm"; fi
}

# 커널/initrd 추출 (Debian live-build: live/, Fedora kiwi: images/pxeboot/ + LiveOS/)
BASE=${BASE:-fedora}
mkdir -p "$TMP/mnt"
if mount -o loop,ro "$ISO" "$TMP/mnt"; then
    if [ -d "$TMP/mnt/live" ]; then
        BASE=debian; LIVEDIR="$TMP/mnt/live"
    elif [ -d "$TMP/mnt/boot/x86_64/loader" ]; then
        BASE=fedora; LIVEDIR="$TMP/mnt/boot/x86_64/loader"      # kiwi
    else
        BASE=fedora; LIVEDIR="$TMP/mnt/images/pxeboot"          # lorax
    fi
    find "$LIVEDIR" -maxdepth 1 -printf '%f\n' > "$OUT/iso-live-dir.txt"
    KERNEL=$(find "$LIVEDIR" -maxdepth 1 \( -name 'vmlinuz*' -o -name 'linux' \) | head -1)
    INITRD=$(find "$LIVEDIR" -maxdepth 1 -name 'initrd*' | head -1)
    for g in "$TMP/mnt/boot/grub2/grub.cfg" "$TMP/mnt/EFI/BOOT/grub.cfg" "$TMP/mnt/boot/grub/grub.cfg"; do
        [ -f "$g" ] && { echo "### $g"; cat "$g"; } >> "$OUT/iso-grub.cfg"
    done
    cp "$KERNEL" "$TMP/vmlinuz"; cp "$INITRD" "$TMP/initrd.img"
    # shellcheck disable=SC2012  # 사람이 읽는 목록 보고용
    ls -laR "$TMP/mnt" 2>/dev/null | head -80 > "$OUT/iso-layout.txt"
    # 루트 이미지에서 검증용 파일 추출 (kiwi: LiveOS/squashfs.img 안의 LiveOS/rootfs.img)
    if command -v unsquashfs >/dev/null 2>&1 && [ -f "$TMP/mnt/LiveOS/squashfs.img" ]; then
        mkdir -p "$OUT/rootfs" "$TMP/rootmnt"
        if unsquashfs -q -n -d "$TMP/sq" "$TMP/mnt/LiveOS/squashfs.img" >/dev/null 2>&1; then
            img=$(find "$TMP/sq" -name 'rootfs.img' | head -1)
            if [ -n "$img" ] && mount -o loop,ro "$img" "$TMP/rootmnt" 2>/dev/null; then
                for f in usr/share/backgrounds/kiyu/default.png etc/xdg/xfce4/panel/default.xml etc/xdg/xdg-kiyu/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml; do
                    [ -f "$TMP/rootmnt/$f" ] && cp "$TMP/rootmnt/$f" "$OUT/rootfs/$(basename "$f")"
                done
                ls -la "$TMP/rootmnt/usr/share/backgrounds/" "$TMP/rootmnt/usr/share/backgrounds/kiyu/" > "$OUT/rootfs/backgrounds-ls.txt" 2>&1
                umount "$TMP/rootmnt"
                note "rootfs: files extracted to results/rootfs"
            else
                note "rootfs: rootfs.img not found/mountable"
            fi
            rm -rf "$TMP/sq"
        else
            note "rootfs: unsquashfs failed"
        fi
    fi
    umount "$TMP/mnt"
    note "base: $BASE kernel: $(basename "$KERNEL") initrd: $(basename "$INITRD")"
else
    note "FAIL: ISO mount"
    exit 1
fi
VOLID=$(blkid -o value -s LABEL "$ISO" 2>/dev/null || true)
if [ "$BASE" = fedora ]; then
    APPEND="root=live:CDLABEL=${VOLID} rd.live.image console=tty0 console=ttyS0,115200 systemd.show_status=1"
    GUEST_USER=liveuser; GUEST_PASS=""
else
    APPEND="boot=live components apparmor=1 security=apparmor locales=ko_KR.UTF-8 keyboard-layouts=kr timezone=Asia/Seoul username=live hostname=kiyu console=tty0 console=ttyS0,115200 systemd.show_status=1"
    GUEST_USER=live; GUEST_PASS=live
fi
note "volid: ${VOLID:-?}"

COMMON=(-m 2048 -smp 2 -display none -vga std -device virtio-net-pci,netdev=n0 -netdev user,id=n0 -usb -device usb-tablet -no-reboot)

########## 1) BIOS + 직접 커널 부팅 (시리얼 콘솔) ##########
note "== BIOS direct-kernel boot"
qemu-system-x86_64 "${KVM[@]}" "${COMMON[@]}" -cdrom "$ISO" \
    -kernel "$TMP/vmlinuz" -initrd "$TMP/initrd.img" \
    -append "$APPEND" \
    -serial "unix:$TMP/serial,server,nowait" -monitor "unix:$TMP/mon1,server,nowait" \
    -pidfile "$TMP/qemu1.pid" >"$OUT/qemu-bios.log" 2>&1 &
sleep 5
# 시리얼 로그 수집 (백그라운드)
python3 - "$TMP/serial" "$OUT/serial-bios.log" <<'PY' &
import socket, sys
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1])
with open(sys.argv[2], "wb") as f:
    while True:
        d = s.recv(4096)
        if not d: break
        f.write(d); f.flush()
PY
TAIL_PID=$!
for t in 30 60 90 120 "$WAIT"; do
    now=${last:-0}; sleep $((t - now)); last=$t
    shot "$TMP/mon1" "$OUT/bios-${t}s.png"
    if grep -q "Started.*Light Display Manager\|lightdm.service" "$OUT/serial-bios.log" 2>/dev/null && [ "$t" -ge 60 ]; then :; fi
done
kill "$TAIL_PID" 2>/dev/null
# 게스트 안에서 측정
if GUEST_USER="$GUEST_USER" GUEST_PASS="$GUEST_PASS" GUEST_BASE="$BASE" python3 "$HERE/lib/serial-shell.py" "$TMP/serial" "$OUT/guest-report.txt" 200; then note "guest shell: ok"; else note "guest shell: login failed"; fi
shot "$TMP/mon1" "$OUT/bios-final.png"
if [ "$BASE" = fedora ] && [ "${GUEST_PHASES:-1}" = 1 ]; then
    # 2단계: 한글 입력 검증 (메모장에 입력 후 스크린샷), 3단계: 설치 프로그램 브랜딩 (Anaconda 스크린샷)
    if GUEST_USER="$GUEST_USER" GUEST_PASS="$GUEST_PASS" GUEST_BASE="$BASE" python3 "$HERE/lib/serial-shell.py" "$TMP/serial" "$OUT/guest-hangul.txt" 120 hangul; then note "guest hangul probe: ok"; else note "guest hangul probe: failed"; fi
    shot "$TMP/mon1" "$OUT/bios-hangul.png"
    if GUEST_USER="$GUEST_USER" GUEST_PASS="$GUEST_PASS" GUEST_BASE="$BASE" python3 "$HERE/lib/serial-shell.py" "$TMP/serial" "$OUT/guest-installer.txt" 150 installer; then note "guest installer probe: ok"; else note "guest installer probe: failed"; fi
    shot "$TMP/mon1" "$OUT/bios-installer.png"
fi
mon "$TMP/mon1" "quit"; sleep 2; kill "$(cat "$TMP/qemu1.pid" 2>/dev/null)" 2>/dev/null

grep -aE "Started .*Light Display Manager|lightdm|Reached target.*Graphical|Failed to start|FAILED" "$OUT/serial-bios.log" | sed 's/\x1b\[[0-9;]*m//g' | sort -u | head -20 | tee -a "$SUMMARY"
if grep -aq "Light Display Manager\|Graphical Interface" "$OUT/serial-bios.log"; then note "RESULT bios: graphical target reached"; else note "RESULT bios: graphical target NOT seen in serial log"; fi

########## 2) UEFI (OVMF) + ISO 부트로더 ##########
note "== UEFI boot"
CODE=""; VARS=""
for pair in "/usr/share/OVMF/OVMF_CODE_4M.ms.fd:/usr/share/OVMF/OVMF_VARS_4M.ms.fd" \
            "/usr/share/OVMF/OVMF_CODE_4M.fd:/usr/share/OVMF/OVMF_VARS_4M.fd" \
            "/usr/share/OVMF/OVMF_CODE.fd:/usr/share/OVMF/OVMF_VARS.fd"; do
    c=${pair%%:*}; v=${pair##*:}
    if [ -f "$c" ] && [ -f "$v" ]; then CODE=$c; VARS=$v; break; fi
done
if [ -n "$CODE" ]; then
    note "ovmf: $CODE $( [[ $CODE == *.ms.fd ]] && echo '(Secure Boot keys)' )"
    cp "$VARS" "$TMP/vars.fd"
    qemu-system-x86_64 "${KVM[@]}" "${COMMON[@]}" -machine q35 \
        -drive if=pflash,format=raw,readonly=on,file="$CODE" -drive if=pflash,format=raw,file="$TMP/vars.fd" \
        -cdrom "$ISO" -boot d -serial "file:$OUT/serial-uefi.log" -monitor "unix:$TMP/mon2,server,nowait" \
        -pidfile "$TMP/qemu2.pid" >"$OUT/qemu-uefi.log" 2>&1 &
    sleep 12; shot "$TMP/mon2" "$OUT/uefi-menu.png"
    mon "$TMP/mon2" "sendkey ret"   # 부트 메뉴 첫 항목
    last=0
    for t in 45 90 "$WAIT"; do sleep $((t - last)); last=$t; shot "$TMP/mon2" "$OUT/uefi-${t}s.png"; done
    mon "$TMP/mon2" "quit"; sleep 2; kill "$(cat "$TMP/qemu2.pid" 2>/dev/null)" 2>/dev/null
    note "RESULT uefi: screenshots taken (uefi-menu.png, uefi-${WAIT}s.png)"
else
    note "ovmf: not found, UEFI test skipped"
fi

rm -rf "$TMP"
note "done: $OUT"
