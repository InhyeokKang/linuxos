#!/usr/bin/env bash
# 오버레이 조립: base/fedora/root + branding/ + apps/ 를 <dest> 아래 실제 경로로 배치한다.
# ISO 빌드(build-fedora.sh)와 RPM 빌드(build-rpm.sh)가 같이 쓴다.   사용법: assemble-overlay.sh <dest> <os_id>
set -euo pipefail
DEST=${1:?dest}; OS_ID=${2:-kiyu}
cd "$(dirname "$0")/../.."
mkdir -p "$DEST"
cp -a base/fedora/root/. "$DEST/"
mkdir -p "$DEST/usr/share/backgrounds/${OS_ID}" "$DEST/usr/share/icons/hicolor/scalable/apps" \
         "$DEST/usr/src/${OS_ID}" "$DEST/usr/lib/taengja" "$DEST/usr/lib/kiyu-control" "$DEST/usr/lib/kiyu-update" \
         "$DEST/usr/bin" "$DEST/usr/share/applications"
cp branding/wallpaper.svg "$DEST/usr/share/backgrounds/${OS_ID}/default.svg"
cp branding/logo.svg "$DEST/usr/share/icons/hicolor/scalable/apps/${OS_ID}.svg"
cp branding/taengja-icon.svg "$DEST/usr/share/icons/hicolor/scalable/apps/taengja.svg"
cp branding/control-icon.svg "$DEST/usr/share/icons/hicolor/scalable/apps/kiyu-control.svg"
cp branding/update-icon.svg "$DEST/usr/share/icons/hicolor/scalable/apps/kiyu-update.svg"
cp branding/imager-icon.svg "$DEST/usr/share/icons/hicolor/scalable/apps/kiyu-imager.svg"
cp apps/kiyu-superkey/kiyu-superkey.c "$DEST/usr/src/${OS_ID}/"
cp apps/taengja/taengja.py apps/taengja/abp2webkit.py "$DEST/usr/lib/taengja/"
cp apps/taengja/taengja "$DEST/usr/bin/taengja"
cp apps/taengja/taengja.desktop "$DEST/usr/share/applications/taengja.desktop"
cp apps/kiyu-control/kiyu-control.py "$DEST/usr/lib/kiyu-control/"
cp apps/kiyu-control/kiyu-control "$DEST/usr/bin/kiyu-control"
cp apps/kiyu-update/kiyu-update.py "$DEST/usr/lib/kiyu-update/"
cp apps/kiyu-update/kiyu-update "$DEST/usr/bin/kiyu-update"
cp apps/kiyu-update/kiyu-update.desktop "$DEST/usr/share/applications/kiyu-update.desktop"
cp apps/kiyu-imager/kiyu-imager.py "$DEST/usr/lib/kiyu-imager/"
cp apps/kiyu-imager/kiyu-imager-write "$DEST/usr/lib/kiyu-imager/"
cp apps/kiyu-imager/kiyu-imager "$DEST/usr/bin/kiyu-imager"
cp apps/kiyu-imager/kiyu-imager.desktop "$DEST/usr/share/applications/kiyu-imager.desktop"
chmod 0755 "$DEST/usr/bin/taengja" "$DEST/usr/bin/kiyu-control" "$DEST/usr/bin/kiyu-update" "$DEST/usr/bin/kiyu-imager" \
           "$DEST/usr/lib/taengja/"*.py "$DEST/usr/lib/kiyu-control/"*.py "$DEST/usr/lib/kiyu-update/"*.py \
           "$DEST/usr/lib/kiyu-imager/kiyu-imager.py" "$DEST/usr/lib/kiyu-imager/kiyu-imager-write"
