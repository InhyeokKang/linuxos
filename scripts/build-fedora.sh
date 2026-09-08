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
# 큰 임시 파일(루트 이미지 수 GB)은 KIYU_BUILD_DIR 아래에 (CI 에서는 /mnt 의 큰 디스크)
BUILD_DIR=${KIYU_BUILD_DIR:-$DESC/.build}
WORK=$BUILD_DIR/desc
TMP=$BUILD_DIR/tmp
if [ "${1:-}" = "--clean" ]; then rm -rf "$OUT" "$BUILD_DIR" "$DESC/.work"; exit 0; fi

for tool in kiwi-ng rsvg-convert xorriso mksquashfs; do
    command -v "$tool" >/dev/null 2>&1 || { echo "필요한 도구가 없습니다: $tool (dnf install kiwi-cli kiwi-systemdeps librsvg2-tools)" >&2; exit 1; }
done

VOLID="${OS_ID}-${OS_VERSION}"          # ≤ 32자, 라이브 부팅의 root=live:CDLABEL 과 일치
rm -rf "$WORK" "$BUILD_DIR/build"; mkdir -p "$WORK" "$TMP" "$OUT"
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
mkdir -p "$WORK/root/usr/src/${OS_ID}" "$WORK/root/usr/lib/taengja" "$WORK/root/usr/bin" "$WORK/root/usr/share/applications" "$WORK/root/usr/share/icons/hicolor/scalable/apps"
cp apps/kiyu-superkey/kiyu-superkey.c "$WORK/root/usr/src/${OS_ID}/"
cp apps/taengja/taengja.py apps/taengja/abp2webkit.py "$WORK/root/usr/lib/taengja/"
cp apps/taengja/taengja "$WORK/root/usr/bin/taengja"
cp apps/taengja/taengja.desktop "$WORK/root/usr/share/applications/taengja.desktop"
cp branding/taengja-icon.svg "$WORK/root/usr/share/icons/hicolor/scalable/apps/taengja.svg"
chmod 0755 "$WORK/root/usr/bin/taengja" "$WORK/root/usr/lib/taengja/taengja.py" "$WORK/root/usr/lib/taengja/abp2webkit.py"
mkdir -p "$WORK/root/usr/lib/kiyu-control"
cp apps/kiyu-control/kiyu-control.py "$WORK/root/usr/lib/kiyu-control/"
cp apps/kiyu-control/kiyu-control "$WORK/root/usr/bin/kiyu-control"
cp branding/control-icon.svg "$WORK/root/usr/share/icons/hicolor/scalable/apps/kiyu-control.svg"
chmod 0755 "$WORK/root/usr/bin/kiyu-control" "$WORK/root/usr/lib/kiyu-control/kiyu-control.py"
mkdir -p "$WORK/root/usr/lib/kiyu-update"
cp apps/kiyu-update/kiyu-update.py "$WORK/root/usr/lib/kiyu-update/"
cp apps/kiyu-update/kiyu-update "$WORK/root/usr/bin/kiyu-update"
cp apps/kiyu-update/kiyu-update.desktop "$WORK/root/usr/share/applications/kiyu-update.desktop"
cp branding/update-icon.svg "$WORK/root/usr/share/icons/hicolor/scalable/apps/kiyu-update.svg"
chmod 0755 "$WORK/root/usr/bin/kiyu-update" "$WORK/root/usr/lib/kiyu-update/kiyu-update.py"

KEYS=()
k="/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-${FEDORA_RELEASE}-primary"
[ -f "$k" ] && KEYS+=(--signing-key "$k")

echo "==> kiwi-ng system build (${OS_NAME} ${OS_VERSION}, Fedora ${FEDORA_RELEASE})"
start=$(date +%s)
kiwi-ng --color-output --logfile "$OUT/build.log" --temp-dir "$TMP" system build \
    --description "$WORK" --target-dir "$BUILD_DIR/build" "${KEYS[@]}"
end=$(date +%s)

iso=$(find "$BUILD_DIR/build" -maxdepth 1 -name '*.iso' | head -1)
[ -n "$iso" ] || { echo "빌드 실패: ISO 없음. $OUT/build.log 확인" >&2; exit 1; }
final="$OUT/${OS_ID}-${OS_VERSION}-x86_64.iso"
mv "$iso" "$final"
pk=$(find "$BUILD_DIR/build" -maxdepth 1 -name '*.packages' | head -1)
[ -n "$pk" ] && mv "$pk" "${final}.packages"
rm -rf "$BUILD_DIR/build" "$TMP"   # 수 GB 임시 파일 정리
sha256sum "$final" > "${final}.sha256"
echo "==> 완료: $final ($(du -h "$final" | cut -f1), $(( (end - start) / 60 ))분)"
