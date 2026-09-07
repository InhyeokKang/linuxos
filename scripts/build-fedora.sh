#!/usr/bin/env bash
# Fedora 기반 ISO 빌드 (kiwi-ng). Fedora 호스트/컨테이너에서 root 로 실행하세요.
#   sudo ./scripts/build-fedora.sh            # 전체 빌드 → base/fedora/out/*.iso
#   sudo ./scripts/build-fedora.sh --clean
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
. ./os.conf
[ "$(id -u)" -eq 0 ] || { echo "root 권한이 필요합니다: sudo $0 $*" >&2; exit 1; }

DESC=base/fedora
OUT=$DESC/out
WORK=$DESC/.work
if [ "${1:-}" = "--clean" ]; then rm -rf "$OUT" "$WORK"; exit 0; fi

for tool in kiwi-ng rsvg-convert xorriso mksquashfs; do
    command -v "$tool" >/dev/null 2>&1 || { echo "필요한 도구가 없습니다: $tool (dnf install kiwi-cli kiwi-systemdeps librsvg2-tools)" >&2; exit 1; }
done

VOLID="${OS_ID}-${OS_VERSION}"          # ≤ 32자, 라이브 부팅의 root=live:CDLABEL 과 일치
rm -rf "$WORK"; mkdir -p "$WORK" "$OUT"
cp -a "$DESC/root" "$DESC/config.sh" "$WORK/"
sed -e "s|@@OS_ID@@|${OS_ID}|g" -e "s|@@OS_NAME@@|${OS_NAME}|g" -e "s|@@OS_VERSION@@|${OS_VERSION}|g" \
    -e "s|@@OS_HOME_URL@@|${OS_HOME_URL}|g" -e "s|@@FEDORA_RELEASE@@|${FEDORA_RELEASE}|g" \
    -e "s|@@FEDORA_MIRROR@@|${FEDORA_MIRROR}|g" -e "s|@@VOLID@@|${VOLID}|g" \
    "$DESC/kiyu.kiwi" > "$WORK/config.xml"

# 정체성 파일 (os-release / issue) 생성 → 오버레이에 포함
mkdir -p "$WORK/root/usr/lib/${OS_ID}"
cat > "$WORK/root/usr/lib/${OS_ID}/os-release" <<OSREL
NAME="${OS_NAME}"
VERSION="${OS_VERSION} (${OS_CODENAME})"
ID=${OS_ID}
ID_LIKE=fedora
VERSION_ID=${OS_VERSION}
VERSION_CODENAME=${OS_CODENAME}
PLATFORM_ID="platform:f${FEDORA_RELEASE}"
PRETTY_NAME="${OS_NAME} ${OS_VERSION} (${OS_CODENAME})"
ANSI_COLOR="0;38;2;244;124;12"
LOGO=${OS_ID}
HOME_URL="${OS_HOME_URL}"
SUPPORT_URL="${OS_HOME_URL}"
BUG_REPORT_URL="${OS_BUG_URL}"
REDHAT_BUGZILLA_PRODUCT="Fedora"
REDHAT_BUGZILLA_PRODUCT_VERSION=${FEDORA_RELEASE}
REDHAT_SUPPORT_PRODUCT="Fedora"
REDHAT_SUPPORT_PRODUCT_VERSION=${FEDORA_RELEASE}
OSREL
printf '%s %s \\n \\l\n\n' "${OS_NAME}" "${OS_VERSION}" > "$WORK/root/usr/lib/${OS_ID}/issue"

# 브랜딩 원본 동기화 (branding/ 이 단일 소스)
mkdir -p "$WORK/root/usr/share/backgrounds/${OS_ID}" "$WORK/root/usr/share/icons/hicolor/scalable/apps"
cp branding/wallpaper.svg "$WORK/root/usr/share/backgrounds/${OS_ID}/default.svg"
cp branding/logo.svg "$WORK/root/usr/share/icons/hicolor/scalable/apps/${OS_ID}.svg"

# 자체 앱 (apps/) 을 오버레이에 배치
mkdir -p "$WORK/root/usr/src/${OS_ID}" "$WORK/root/usr/lib/${OS_ID}-browser" "$WORK/root/usr/bin" "$WORK/root/usr/share/applications" "$WORK/root/usr/share/icons/hicolor/scalable/apps"
cp apps/kiyu-superkey/kiyu-superkey.c "$WORK/root/usr/src/${OS_ID}/"
cp apps/kiyu-browser/kiyu-browser.py "$WORK/root/usr/lib/${OS_ID}-browser/"
cp apps/kiyu-browser/kiyu-browser "$WORK/root/usr/bin/${OS_ID}-browser"
cp apps/kiyu-browser/kiyu-browser.desktop "$WORK/root/usr/share/applications/${OS_ID}-browser.desktop"
cp branding/browser-icon.svg "$WORK/root/usr/share/icons/hicolor/scalable/apps/${OS_ID}-browser.svg"
chmod 0755 "$WORK/root/usr/bin/${OS_ID}-browser" "$WORK/root/usr/lib/${OS_ID}-browser/kiyu-browser.py"

KEYS=()
k="/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-${FEDORA_RELEASE}-primary"
[ -f "$k" ] && KEYS+=(--signing-key "$k")

echo "==> kiwi-ng system build (${OS_NAME} ${OS_VERSION}, Fedora ${FEDORA_RELEASE})"
start=$(date +%s)
kiwi-ng --color-output --logfile "$OUT/build.log" system build \
    --description "$WORK" --target-dir "$OUT/build" "${KEYS[@]}"
end=$(date +%s)

iso=$(find "$OUT/build" -maxdepth 1 -name '*.iso' | head -1)
[ -n "$iso" ] || { echo "빌드 실패: ISO 없음. $OUT/build.log 확인" >&2; exit 1; }
final="$OUT/${OS_ID}-${OS_VERSION}-x86_64.iso"
mv "$iso" "$final"
[ -f "${iso}.packages" ] && mv "${iso}.packages" "${final}.packages" || find "$OUT/build" -name '*.packages' -exec mv {} "${final}.packages" \; 2>/dev/null || true
sha256sum "$final" > "${final}.sha256"
echo "==> 완료: $final ($(du -h "$final" | cut -f1), $(( (end - start) / 60 ))분)"
