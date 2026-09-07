#!/bin/sh
# kiyu: 배포판 기본 설정 디렉터리를 XDG_CONFIG_DIRS 맨 앞에 두고, D-Bus/systemd --user 활성화 환경에도 전파.
# (50-systemd-user.sh 뒤에 실행되도록 55 번호)
case ":${XDG_CONFIG_DIRS:-}:" in
  *:/etc/xdg/xdg-kiyu:*) ;;
  *) XDG_CONFIG_DIRS="/etc/xdg/xdg-kiyu:${XDG_CONFIG_DIRS:-/etc/xdg}" ;;
esac
export XDG_CONFIG_DIRS
if command -v dbus-update-activation-environment >/dev/null 2>&1; then
    dbus-update-activation-environment --systemd XDG_CONFIG_DIRS GTK_IM_MODULE QT_IM_MODULE XMODIFIERS 2>/dev/null \
    || dbus-update-activation-environment XDG_CONFIG_DIRS 2>/dev/null || true
fi
