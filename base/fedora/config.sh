#!/bin/bash
# kiwi 가 패키지 설치와 root/ 오버레이 복사 후 이미지 chroot 안에서 실행하는 스크립트.
# (Debian 트리의 hooks/normal/* 에 해당)
set -euxo pipefail
OS_ID=kiyu

# ---- 정체성 -----------------------------------------------------------------
if [ -f "/usr/lib/${OS_ID}/os-release" ]; then
    rm -f /etc/os-release
    cp "/usr/lib/${OS_ID}/os-release" /usr/lib/os-release
    ln -s ../usr/lib/os-release /etc/os-release
fi
[ -f "/usr/lib/${OS_ID}/issue" ] && cp "/usr/lib/${OS_ID}/issue" /etc/issue

# ---- 라이브 세션 (livesys-scripts) ---------------------------------------------
cat > /etc/sysconfig/livesys <<'LIVESYS'
livesys_session="xfce"
LIVESYS

# ---- 디스플레이 매니저 / 세션 ----------------------------------------------------
systemctl set-default graphical.target
systemctl enable lightdm.service 2>/dev/null || echo "WARN: cannot enable lightdm"
echo "/usr/sbin/lightdm" > /etc/X11/default-display-manager 2>/dev/null || true

# ---- 보안 / 서비스 -----------------------------------------------------------
en() { systemctl enable "$1" 2>/dev/null || echo "WARN: cannot enable $1"; }
en nftables.service
systemctl disable firewalld.service 2>/dev/null || true
en dnf5-automatic.timer || en dnf-automatic.timer
en fstrim.timer
en NetworkManager.service
en chronyd.service
en kiyu-firstboot.service
en livesys.service; en livesys-late.service
systemctl disable ModemManager.service 2>/dev/null || true
# Ctrl+Alt+Del 로 콘솔에서 재부팅되지 않게 (Fedora 는 /etc 에 링크가 이미 있어 mask 대신 직접 /dev/null 로)
rm -f /etc/systemd/system/ctrl-alt-del.target
ln -s /dev/null /etc/systemd/system/ctrl-alt-del.target
# 방화벽 규칙 문법 검사 (빌드 단계에서 오류를 잡음)
nft -c -f /etc/nftables/kiyu.nft
passwd -l root >/dev/null 2>&1 || true
sed -i 's/^\(HOME_MODE\s\+\).*/\10700/' /etc/login.defs 2>/dev/null || true

# ---- 브랜딩 이미지 (SVG -> PNG) ----------------------------------------------
BG=/usr/share/backgrounds/${OS_ID}
[ -f "${BG}/default.svg" ] && rsvg-convert -w 3840 -h 2160 "${BG}/default.svg" -o "${BG}/default.png"
ICON=/usr/share/icons/hicolor/scalable/apps/${OS_ID}.svg
if [ -f "${ICON}" ]; then
    mkdir -p /usr/share/pixmaps
    rsvg-convert -w 48 -h 48 "${ICON}" -o "/usr/share/pixmaps/${OS_ID}.png"
fi
# XFCE/Fedora 기본 배경 파일들을 우리 배경으로 교체 (xfdesktop 4.20 은 첫 로그인에 컴파일된 기본 파일을 씀;
# Fedora 는 /usr/share/backgrounds/default.png(.xml) 과 images/ 아래를 기본으로 가리킴)
if [ -f "${BG}/default.svg" ]; then
    find /usr/share/backgrounds -maxdepth 2 -type f ! -path "${BG}/*" \
        \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.svg' -o -name '*.webp' -o -name '*.jxl' \) | while read -r f; do
        case "$f" in *.svg) cp "${BG}/default.svg" "$f" ;; *) cp "${BG}/default.png" "$f" ;; esac
    done
    # 슬라이드쇼 xml 은 우리 png 하나만 가리키게
    find /usr/share/backgrounds -maxdepth 3 -type f -name '*.xml' | while read -r f; do
        printf '<background><static><duration>86400</duration><file>%s</file></static></background>\n' "${BG}/default.png" > "$f"
    done
    # xfdesktop(Fedora) 의 컴파일된 기본 경로: images/default.png 가 최우선 → 우리 png 로 생성
    mkdir -p /usr/share/backgrounds/images
    for f in /usr/share/backgrounds/images/default.png /usr/share/backgrounds/default.png; do
        rm -f "$f"; cp "${BG}/default.png" "$f"
    done
    # Fedora 기본 jxl 원본(f*/default/*.jxl)도 우리 png 내용으로 (심볼릭 링크 대상 교체)
    find /usr/share/backgrounds -maxdepth 3 -type f -name '*.jxl' -exec cp "${BG}/default.png" {} \;
fi
# Plank 독 기본값 (dconf 시스템 DB)
command -v dconf >/dev/null 2>&1 && dconf update
# 패널 플러그인 in-process (wrapper 프로세스 제거)
for plug in whiskermenu launcher tasklist clock showdesktop separator notification-plugin systray; do
    d="/usr/share/xfce4/panel/plugins/${plug}.desktop"
    [ -f "$d" ] || continue
    if grep -q '^X-XFCE-Internal=' "$d"; then sed -i 's/^X-XFCE-Internal=.*/X-XFCE-Internal=true/' "$d"; else printf 'X-XFCE-Internal=true\n' >> "$d"; fi
done
# 프린터 큐 트레이 애플릿 끔 (메모리)
for f in /etc/xdg/autostart/print-applet.desktop /etc/xdg/autostart/system-config-printer-applet.desktop; do
    if [ -f "$f" ] && ! grep -q '^Hidden=' "$f"; then echo 'Hidden=true' >> "$f"; fi
done

# ---- kiyu-superkey 컴파일 (Super 탭 → 시작 메뉴; 소스는 apps/kiyu-superkey) ----------
if [ -f /usr/src/kiyu/kiyu-superkey.c ] && command -v gcc >/dev/null 2>&1; then
    gcc -O2 -o /usr/bin/kiyu-superkey /usr/src/kiyu/kiyu-superkey.c -lX11 -lXtst
    chmod 0755 /usr/bin/kiyu-superkey
    echo "kiyu-superkey built"
fi

# ---- 기본 앱 / 권한 --------------------------------------------------------------
chmod 0755 /usr/bin/startkiyu /usr/lib/${OS_ID}/* /usr/local/bin/* /etc/X11/xinit/xinitrc.d/*.sh 2>/dev/null || true
gtk-update-icon-cache -f -q /usr/share/icons/hicolor || true
update-desktop-database -q || true
fc-cache -f || true

# ---- SELinux 라벨 -------------------------------------------------------------
if [ -x /usr/sbin/setfiles ] && [ -f /etc/selinux/targeted/contexts/files/file_contexts ]; then
    setfiles -F -e /proc -e /sys -e /dev -e /run /etc/selinux/targeted/contexts/files/file_contexts / || true
fi

# ---- 글꼴: IBM Plex Sans KR / Inter (있으면), Pretendard (GitHub 릴리스, 실패해도 빌드는 계속) --------
dnf -y install --setopt=install_weak_deps=False ibm-plex-sans-kr-fonts rsms-inter-fonts 2>/dev/null \
    || dnf -y install --setopt=install_weak_deps=False ibm-plex-sans-kr-fonts 2>/dev/null || echo "WARN: optional fonts not installed"
PRET_VER=1.3.9
if curl -fsSL --retry 2 -o /tmp/pretendard.zip "https://github.com/orioncactus/pretendard/releases/download/v${PRET_VER}/Pretendard-${PRET_VER}.zip"; then
    mkdir -p /usr/share/fonts/pretendard
    unzip -qo -j /tmp/pretendard.zip '*/variable/PretendardVariable.ttf' -d /usr/share/fonts/pretendard/ \
        || unzip -qo -j /tmp/pretendard.zip '*PretendardVariable.ttf' -d /usr/share/fonts/pretendard/ || true
    rm -f /tmp/pretendard.zip
    ls /usr/share/fonts/pretendard/ || true
else
    echo "WARN: Pretendard download failed; falling back to Plex/Source Han"
fi
fc-cache -f || true

# ---- ld.so 캐시 (없으면 첫 부팅에 ldconfig.service 가 16초 걸림) ----------------------
ldconfig || true

# ---- 정리 ----------------------------------------------------------------------
dnf5 clean all 2>/dev/null || dnf clean all 2>/dev/null || true
rm -rf /var/cache/dnf /var/cache/libdnf5 /tmp/* /var/tmp/*
rm -f /etc/machine-id; touch /etc/machine-id
exit 0
