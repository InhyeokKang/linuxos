#!/usr/bin/env bash
# ISO 를 굽지 않고 데스크톱 UI 만 미리 봅니다.
# Debian/Ubuntu 머신(또는 컨테이너)에 XFCE 와 kiyu 설정 트리를 올리고 Xvfb 에서 띄운 뒤 스크린샷을 찍습니다.
#   sudo ./scripts/preview-desktop.sh            # 설치 + 세션 시작 + 스크린샷 (out/preview/*.png)
#   sudo ./scripts/preview-desktop.sh --shots    # 이미 실행 중인 세션에서 스크린샷만
# 실제 ISO 와의 차이: 호스트 배포판의 XFCE 버전을 쓰고, Firefox/LibreOffice 등 앱은 설치하지 않습니다.
set -euo pipefail
cd "$(dirname "$0")/.."
A=base/fedora/root
D=base/debian/config/includes.chroot_after_packages
OUT=out/preview
DISP=:99
mkdir -p "$OUT"

[ "$(id -u)" -eq 0 ] || { echo "root 권한이 필요합니다 (sudo)." >&2; exit 1; }

install_and_overlay() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y -qq --no-install-recommends \
        xvfb dbus-x11 x11-utils xdotool imagemagick locales \
        xfce4-session xfce4-panel xfce4-settings xfwm4 xfdesktop4 xfconf xfce4-appfinder \
        xfce4-whiskermenu-plugin picom xfce4-power-manager xfce4-power-manager-plugins \
        xfce4-notifyd xfce4-screenshooter xfce4-taskmanager xfce4-terminal xfce4-clipman-plugin \
        thunar tumbler mousepad ristretto galculator xarchiver mate-polkit xcape \
        arc-theme gtk2-engines-murrine papirus-icon-theme adwaita-icon-theme \
        fonts-noto-core fonts-noto-cjk fonts-noto-mono librsvg2-bin librsvg2-common gvfs
    sed -i 's/^# *ko_KR.UTF-8 UTF-8/ko_KR.UTF-8 UTF-8/' /etc/locale.gen
    grep -q '^ko_KR.UTF-8' /etc/locale.gen || echo 'ko_KR.UTF-8 UTF-8' >> /etc/locale.gen
    locale-gen >/dev/null

    # 라이브 이미지에서 includes 가 하는 일을 그대로 재현
    cp -a "$A/etc/xdg/xdg-kiyu" /etc/xdg/
    cp -a "$A/etc/fonts/conf.d/." /etc/fonts/conf.d/
    cp -a "$D/etc/X11/Xsession.d/." /etc/X11/Xsession.d/
    mkdir -p "$HOME/.config/gtk-3.0" && cp -a "$A/etc/skel/.config/gtk-3.0/gtk.css" "$HOME/.config/gtk-3.0/gtk.css"
    cp -a "$A/usr/bin/startkiyu" /usr/bin/
    cp -a "$A/usr/lib/kiyu" /usr/lib/
    mkdir -p /usr/share/themes && cp -a "$A/usr/share/themes/kiyu" /usr/share/themes/
    # ISO 와 같이 패널 플러그인을 in-process 로 (config.sh 와 동일 목록 + 프리뷰 대체 플러그인)
    for plug in whiskermenu docklike launcher tasklist clock showdesktop separator notification-plugin systray; do
        d="/usr/share/xfce4/panel/plugins/${plug}.desktop"; [ -f "$d" ] || continue
        if grep -q '^X-XFCE-Internal=' "$d"; then sed -i 's/^X-XFCE-Internal=.*/X-XFCE-Internal=true/' "$d"; else printf 'X-XFCE-Internal=true\n' >> "$d"; fi
    done
    mkdir -p /usr/lib/kiyu-control && cp -a apps/kiyu-control/kiyu-control.py /usr/lib/kiyu-control/ && cp -a apps/kiyu-control/kiyu-control /usr/bin/
    cp -a branding/control-icon.svg /usr/share/icons/hicolor/scalable/apps/kiyu-control.svg
    cp -a "$A/usr/share/backgrounds/kiyu" /usr/share/backgrounds/
    cp -a "$A/usr/share/icons/hicolor/scalable/apps/kiyu.svg" /usr/share/icons/hicolor/scalable/apps/
    cp -a branding/taengja-icon.svg /usr/share/icons/hicolor/scalable/apps/taengja.svg
    cp -a "$A/usr/share/applications/." /usr/share/applications/
    cp -a "$D/usr/share/applications/kiyu-install.desktop" /usr/share/applications/ 2>/dev/null || true
    cp -a "$A/usr/local/bin/." /usr/local/bin/
    chmod +x /usr/bin/startkiyu /usr/lib/kiyu/* /usr/local/bin/kiyu-*

    # 훅(0100-identity)이 하는 일 중 UI 에 관계된 부분
    cp branding/wallpaper.svg /usr/share/backgrounds/kiyu/default.svg; rsvg-convert -w 3840 -h 2160 /usr/share/backgrounds/kiyu/default.svg -o /usr/share/backgrounds/kiyu/default.png
    mkdir -p /usr/share/pixmaps
    rsvg-convert -w 48 -h 48 /usr/share/icons/hicolor/scalable/apps/kiyu.svg -o /usr/share/pixmaps/kiyu.png
    default_bg=$(strings /usr/bin/xfdesktop | grep -m1 '^/usr/share/backgrounds/' || true)
    if [ -n "$default_bg" ]; then
        mkdir -p "$(dirname "$default_bg")"
        if [ -e "$default_bg" ] && ! dpkg-divert --list "$default_bg" | grep -q .; then
            dpkg-divert --package kiyu --add --rename --divert "${default_bg}.distrib" "$default_bg"
        fi
        cp /usr/share/backgrounds/kiyu/default.svg "$default_bg"
    fi
    # 호스트에 docklike 플러그인이 없으면 프리뷰에서만 런처 3개 + 아이콘 전용 tasklist(id 20~23) 로 흉내낸다
    if ! ls /usr/lib/*/xfce4/panel/plugins/libdocklike.so >/dev/null 2>&1; then
        python3 - <<'PYX'
p = "/etc/xdg/xdg-kiyu/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"
s = open(p).read()
s = s.replace('<value type="int" value="2"/>', ''.join('<value type="int" value="%d"/>' % i for i in (20, 21, 22, 23)), 1)
launcher = '<property name="plugin-%d" type="string" value="launcher"><property name="items" type="array"><value type="string" value="/usr/share/applications/%s.desktop"/></property><property name="show-label" type="bool" value="false"/></property>'
s = s.replace('<property name="plugin-2" type="string" value="docklike"/>',
              launcher % (20, "thunar") + launcher % (21, "taengja") + launcher % (22, "org.gnome.Software") +
              '<property name="plugin-23" type="string" value="tasklist"><property name="show-labels" type="bool" value="false"/><property name="flat-buttons" type="bool" value="true"/><property name="grouping" type="bool" value="true"/><property name="show-handle" type="bool" value="false"/></property>')
open(p, "w").write(s)
PYX
    fi
    gtk-update-icon-cache -f -q /usr/share/icons/hicolor || true
    fc-cache -f >/dev/null || true
    update-desktop-database -q || true

    # 앱이 없어도 런처/즐겨찾기 아이콘이 보이도록 자리표시자
    for app in "firefox-esr|Firefox|firefox" "org.gnome.Software|소프트웨어|system-software-install" "libreoffice-writer|LibreOffice Writer|libreoffice-writer" "taengja|탱자|taengja"; do
        IFS='|' read -r id name icon <<<"$app"
        [ -f "/usr/share/applications/$id.desktop" ] || printf '[Desktop Entry]\nType=Application\nName=%s\nExec=xmessage %s\nIcon=%s\nCategories=Utility;\n' "$name" "$name" "$icon" > "/usr/share/applications/$id.desktop"
    done
}

start_session() {
    for p in xfce4-session xfce4-panel xfdesktop xfwm4 xfsettingsd xfconfd xfce4-notifyd xcape picom Xvfb; do pkill -x "$p" 2>/dev/null || true; done
    sleep 1
    rm -rf "$HOME/.config/xfce4" "$HOME/.cache/sessions" "$HOME/.cache/xfce4"
    cat > "$OUT/session.sh" <<SESSION
#!/bin/bash
export DISPLAY=$DISP LANG=ko_KR.UTF-8 LC_ALL=ko_KR.UTF-8 DESKTOP_SESSION=kiyu
Xvfb $DISP -screen 0 1600x900x24 -nolisten tcp >/dev/null 2>&1 &
sleep 2
. /etc/X11/Xsession.d/15kiyu-xdg-config-dirs
eval "\$(dbus-launch --sh-syntax)"
export DBUS_SESSION_BUS_ADDRESS
echo "\$DBUS_SESSION_BUS_ADDRESS" > "$OUT/dbus.addr"
startkiyu >"$OUT/session.log" 2>&1 &
SESSION
    chmod +x "$OUT/session.sh"
    nohup setsid "$OUT/session.sh" >/dev/null 2>&1 &
    sleep 20
}

shots() {
    export DISPLAY=$DISP XDG_CONFIG_DIRS=/etc/xdg/xdg-kiyu:/etc/xdg HOME=${HOME:-/root} LANG=ko_KR.UTF-8
    DBUS_SESSION_BUS_ADDRESS=$(cat "$OUT/dbus.addr"); export DBUS_SESSION_BUS_ADDRESS
    import -window root "$OUT/01-desktop.png"
    xdotool key alt+F1; sleep 2; import -window root "$OUT/02-start-menu.png"; xdotool key Escape; sleep 1
    setsid thunar "$PWD" >/dev/null 2>&1 & sleep 3
    setsid mousepad README.md >/dev/null 2>&1 & sleep 4
    m=$(xdotool search --class mousepad | tail -1); xdotool windowsize "$m" 760 520; xdotool windowmove "$m" 800 60
    t=$(xdotool search --class thunar | tail -1); xdotool windowsize "$t" 720 480; xdotool windowmove "$t" 40 80; sleep 1
    import -window root "$OUT/03-windows.png"
    xdotool key ctrl+shift+Escape; sleep 3; import -window root "$OUT/04-task-manager.png"
    echo "스크린샷: $OUT/*.png"
}

case "${1:-}" in
    --shots) shots ;;
    *) install_and_overlay; start_session; shots ;;
esac
