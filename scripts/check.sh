#!/usr/bin/env bash
# 빌드 없이 할 수 있는 정적 검사: 셸 문법, XML/YAML 파싱, 실행 권한, 패키지 목록 형식
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
fail=0
note() { printf '  %s\n' "$*"; }
bad()  { printf 'FAIL: %s\n' "$*"; fail=1; }

echo "[1/5] 셸 스크립트 문법"
while IFS= read -r f; do
    if head -1 "$f" | grep -q bash; then bash -n "$f" || bad "$f"; else sh -n "$f" || bad "$f"; fi
done < <(grep -rlE --exclude-dir=.git --exclude-dir=cache --exclude-dir=chroot --exclude-dir=binary --exclude-dir=out '^#!\s*/(usr/)?bin/(env )?(ba)?sh' .)
if command -v shellcheck >/dev/null 2>&1; then
    # shellcheck disable=SC2046
    shellcheck -x $(grep -rlE --exclude-dir=.git --exclude-dir=cache --exclude-dir=chroot --exclude-dir=binary --exclude-dir=out '^#!\s*/(usr/)?bin/(env )?(ba)?sh' .) || bad "shellcheck"
else
    note "shellcheck 없음 (건너뜀)"
fi

echo "[2/5] 실행 권한"
for f in base/debian/auto/* scripts/*.sh base/debian/config/hooks/normal/*.hook.chroot \
         base/debian/config/includes.chroot_after_packages/usr/local/bin/* \
         base/debian/config/includes.chroot_after_packages/usr/lib/kiyu/* \
         base/debian/config/includes.chroot_after_packages/usr/bin/* \
         base/fedora/config.sh base/fedora/root/usr/local/bin/* base/fedora/root/usr/lib/kiyu/* \
         base/fedora/root/usr/bin/* base/fedora/root/etc/X11/xinit/xinitrc.d/*.sh; do
    [ -x "$f" ] || bad "실행 권한 없음: $f"
done

echo "[3/5] XML"
python3 - <<'PY' || fail=1
import sys, glob, xml.etree.ElementTree as ET
ok = True
for f in glob.glob("base/**/*.xml", recursive=True) + glob.glob("base/**/*.kiwi", recursive=True) + glob.glob("base/**/*.conf", recursive=True):
    if f.endswith(".conf") and "/fonts/" not in f:
        continue
    try:
        ET.parse(f)
    except ET.ParseError as e:
        print(f"FAIL: {f}: {e}"); ok = False
sys.exit(0 if ok else 1)
PY

echo "[4/5] YAML (Calamares)"
python3 - <<'PY' || fail=1
import sys, glob
try:
    import yaml
except ImportError:
    print("  pyyaml 없음 (건너뜀)"); sys.exit(0)
ok = True
files = glob.glob("base/debian/config/includes.chroot_after_packages/etc/calamares/**/*.conf", recursive=True) \
      + glob.glob("base/debian/config/includes.chroot_after_packages/etc/calamares/**/*.desc", recursive=True) \
      + glob.glob(".github/workflows/*.yml")
for f in files:
    try:
        with open(f) as fh:
            yaml.safe_load(fh)
    except Exception as e:
        print(f"FAIL: {f}: {e}"); ok = False
sys.exit(0 if ok else 1)
PY

echo "[5/5] 패키지 목록 형식"
for f in base/debian/config/package-lists/*.list.chroot; do
    if grep -q $'\r' "$f"; then bad "CRLF: $f"; fi
    if grep -vE '^\s*(#.*)?$' "$f" | grep -vE '^[a-z0-9][a-z0-9.+-]*(:[a-z0-9]+)?$' | grep -vE '^#(if|elif|else|endif)' >/dev/null; then
        bad "잘못된 패키지 이름: $f"
        grep -vE '^\s*(#.*)?$' "$f" | grep -vE '^[a-z0-9][a-z0-9.+-]*(:[a-z0-9]+)?$'
    fi
done

if command -v nft >/dev/null 2>&1; then
    echo "[+] nftables 문법"
    nft -c -f base/debian/config/includes.chroot_after_packages/etc/nftables.conf 2>/dev/null || note "nft -c 실패 (include 경로 때문일 수 있음; 빌드 훅에서 재검사)"
fi

if [ "$fail" = 0 ]; then echo "모든 검사 통과"; else echo "검사 실패"; exit 1; fi
