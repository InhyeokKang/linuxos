#!/usr/bin/env bash
# ISO 빌드. Debian 12/13 (또는 그 컨테이너) 에서 root 로 실행하세요.
#   sudo ./scripts/build.sh            # 전체 빌드
#   sudo ./scripts/build.sh --clean    # 캐시 포함 전부 정리
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$(id -u)" -ne 0 ]; then
    echo "root 권한이 필요합니다: sudo $0 $*" >&2
    exit 1
fi

for tool in lb debootstrap mksquashfs xorriso rsvg-convert; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "필요한 도구가 없습니다: $tool" >&2
        echo "  apt-get install live-build debootstrap squashfs-tools xorriso librsvg2-bin" >&2
        exit 1
    fi
done

if [ "${1:-}" = "--clean" ]; then
    lb clean --purge
    ./auto/clean
    exit 0
fi

# shellcheck disable=SC1091
. ./os.conf

echo "==> lb clean"
lb clean
echo "==> lb config (${OS_NAME} ${OS_VERSION}, ${DEBIAN_DIST}/${ARCH})"
lb config
echo "==> lb build (수십 분 걸립니다; build.log 에 기록)"
start=$(date +%s)
lb build
end=$(date +%s)

iso=$(find . -maxdepth 1 -name "*.iso" | head -1)
if [ -z "$iso" ]; then
    echo "빌드 실패: ISO 가 생성되지 않았습니다. build.log 를 확인하세요." >&2
    exit 1
fi
echo
echo "==> 완료: $iso ($(du -h "$iso" | cut -f1), $(( (end - start) / 60 ))분)"
[ -f "${iso}.sha256" ] || sha256sum "$iso" > "${iso}.sha256"
echo "    sha256: $(cut -d' ' -f1 "${iso}.sha256")"
