#!/bin/sh
# kiyu: XFCE 세션이면 배포판 기본 설정 디렉터리를 XDG_CONFIG_DIRS 맨 앞에 둔다.
# (Fedora 의 lightdm/Xsession 은 /etc/X11/xinit/xinitrc.d/*.sh 를 source 한다)
case "${DESKTOP_SESSION:-}${XDG_SESSION_DESKTOP:-}${XDG_CURRENT_DESKTOP:-}" in
  *kiyu*|*xfce*|*XFCE*)
    XDG_CONFIG_DIRS="/etc/xdg/xdg-kiyu:${XDG_CONFIG_DIRS:-/etc/xdg}"
    export XDG_CONFIG_DIRS
    ;;
esac
