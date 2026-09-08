#!/usr/bin/env bash
# kiyu-desktop RPM 빌드 (Fedora 컨테이너 안에서 실행). 결과: out/rpm/*.rpm
#   BuildRequires: rpm-build gcc libX11-devel libXtst-devel python3 curl
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck source=/dev/null
. ./os.conf
OUT=${KIYU_RPM_OUT:-out/rpm}; mkdir -p "$OUT"
REL=${KIYU_RPM_RELEASE:-$(git rev-list --count HEAD 2>/dev/null || echo 1).$(git rev-parse --short HEAD 2>/dev/null || echo local)}
WORK=$(mktemp -d); SRC="$WORK/kiyu-desktop-${OS_VERSION}"
mkdir -p "$SRC/root"
scripts/lib/assemble-overlay.sh "$SRC/root" "${OS_ID}"
# 탱자 차단 목록 (네트워크 안 되면 건너뜀)
mkdir -p "$SRC/root/usr/share/taengja/filters"
fetch() { curl -fsSL --max-time 60 --retry 2 -o "$2" "$1" 2>/dev/null && [ -s "$2" ]; }
fetch https://easylist.to/easylist/easyprivacy.txt "$WORK/easyprivacy.txt" && python3 apps/taengja/abp2webkit.py --max 30000 --no-cosmetic -o "$SRC/root/usr/share/taengja/filters/10-easyprivacy.json" "$WORK/easyprivacy.txt" || echo "경고: easyprivacy 생략"
fetch https://easylist.to/easylist/easylist.txt "$WORK/easylist.txt" && python3 apps/taengja/abp2webkit.py --max 30000 --no-cosmetic -o "$SRC/root/usr/share/taengja/filters/20-easylist.json" "$WORK/easylist.txt" || echo "경고: easylist 생략"
fetch https://raw.githubusercontent.com/List-KR/List-KR/master/filter.txt "$WORK/listkr.txt" && python3 apps/taengja/abp2webkit.py --max 15000 -o "$SRC/root/usr/share/taengja/filters/30-listkr.json" "$WORK/listkr.txt" || echo "경고: List-KR 생략"
# 소스 tarball + spec
mkdir -p "$WORK/rpmbuild"/{SOURCES,SPECS,BUILD,RPMS,SRPMS}
tar -C "$WORK" -czf "$WORK/rpmbuild/SOURCES/kiyu-desktop-${OS_VERSION}.tar.gz" "kiyu-desktop-${OS_VERSION}"
sed -e "s/@VERSION@/${OS_VERSION}/" -e "s/@RELEASE@/${REL}/" packaging/kiyu-desktop.spec > "$WORK/rpmbuild/SPECS/kiyu-desktop.spec"
rpmbuild --define "_topdir $WORK/rpmbuild" -bb "$WORK/rpmbuild/SPECS/kiyu-desktop.spec"
find "$WORK/rpmbuild/RPMS" -name '*.rpm' -exec cp {} "$OUT/" \;
rm -rf "$WORK"
find "$OUT" -name "*.rpm"
