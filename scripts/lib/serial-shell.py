#!/usr/bin/env python3
"""QEMU 시리얼 콘솔(unix 소켓)로 라이브 세션에 로그인해 명령을 실행하고 결과를 저장합니다.
사용: serial-shell.py <socket> <output-file> [timeout-sec]
"""
import socket, sys, time, re

sock_path, out_path = sys.argv[1], sys.argv[2]
deadline = time.time() + float(sys.argv[3] if len(sys.argv) > 3 else 180)
PHASE = sys.argv[4] if len(sys.argv) > 4 else None  # hangul | installer (기본: 전체 점검)
import os
USER = os.environ.get("GUEST_USER", "live")
PASSWORD = os.environ.get("GUEST_PASS", "live")
BASE = os.environ.get("GUEST_BASE", "debian")
COMMANDS = [
    "echo '=== os-release'; cat /etc/os-release",
    "echo '=== uname'; uname -r; cat /proc/cmdline",
    "echo '=== memory'; free -m; grep -E 'MemTotal|MemAvailable|AnonPages|Shmem:|Slab|SUnreclaim|KernelStack|PageTables' /proc/meminfo",
    "echo '=== zram'; sudo /usr/sbin/zramctl 2>/dev/null || echo none",
    "echo '=== pss by process (MB)'; sudo sh -c 'for p in /proc/[0-9]*; do c=$(cat $p/comm 2>/dev/null); v=$(awk \"/^Pss:/{s+=\\$2}END{print s+0}\" $p/smaps_rollup 2>/dev/null); [ -n \"$v\" ] && [ \"$v\" -gt 0 ] && echo \"$v $c\"; done | sort -rn | awk \"{t+=\\$1; printf \\\"%6.1f %s\\\\n\\\", \\$1/1024, \\$2} END{printf \\\"TOTAL %.0f MB\\\\n\\\", t/1024}\" | head -30'",
    "echo '=== boot time'; systemd-analyze 2>/dev/null; systemd-analyze blame 2>/dev/null | head -12",
    "echo '=== failed units'; systemctl --failed --no-pager --no-legend",
    "echo '=== services'; for s in lightdm nftables firewalld apparmor zramswap dnf5-automatic.timer unattended-upgrades NetworkManager livesys; do printf '%s: %s\\n' $s $(systemctl is-active $s 2>/dev/null); done",
    "echo '=== mac'; cat /sys/kernel/security/lsm 2>&1; echo; getenforce 2>/dev/null; sestatus 2>/dev/null | head -3; systemctl status apparmor --no-pager 2>&1 | head -4",
    "echo '=== firewall'; sudo firewall-cmd --get-default-zone 2>/dev/null; sudo firewall-cmd --list-all 2>/dev/null | head -12; sudo /usr/sbin/nft list ruleset 2>/dev/null | head -8",
    "echo '=== sysctl'; /usr/sbin/sysctl kernel.kptr_restrict kernel.yama.ptrace_scope kernel.unprivileged_bpf_disabled vm.swappiness",
    "echo '=== xsession'; ps -eo comm | grep -E '^(Xorg|lightdm|xfce4-session|xfwm4|xfce4-panel|xfdesktop|xcape|fcitx5|blueman-applet|applet.py|nm-applet)$' | sort | uniq -c",
    "echo '=== wallpaper'; xfconf-query -c xfce4-desktop -l -v 2>/dev/null | grep last-image; ls -la /usr/share/backgrounds/xfce/ 2>&1 | head; dpkg-divert --list '*backgrounds*' 2>&1",
    "echo '=== xfconf-diag'; env | grep XDG_CONFIG_DIRS; systemctl --user show-environment 2>/dev/null | grep XDG_CONFIG_DIRS; ls ~/.config/xfce4/xfconf/xfce-perchannel-xml/ 2>&1; xfconf-query -c xfce4-panel -p /panels/panel-1/plugin-ids 2>&1 | head -3; xfconf-query -c xfce4-panel -l 2>&1 | head -5; rpm -q xfce4-docklike-plugin xfce-polkit mate-polkit 2>&1; ls /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/ 2>&1; ls /usr/libexec/livesys/sessions.d/ 2>&1",
    "echo '=== livesys-xfce'; cat /usr/libexec/livesys/sessions.d/livesys-xfce 2>&1 | grep -v '^#' | grep -v '^$' | head -60; ls -la ~/.config/xfce4/panel/ 2>&1 | head; grep -c whiskermenu ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml 2>&1; xfconf-query -c xfce4-panel -p /panels 2>&1 | tail -3; xfconf-query -c xfce4-panel -p /plugins/plugin-1 2>&1",
    "echo '=== panel-diag'; xfce4-panel --version 2>&1 | head -1; xfconf-query -c xfce4-panel -l -v 2>&1 | head -70; xwininfo -root -tree 2>/dev/null | grep -iE 'xfce4-panel' | head -6; echo '-- user xml'; head -60 ~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml 2>&1; echo '-- default.xml'; grep -c whiskermenu /etc/xdg/xfce4/panel/default.xml 2>&1; echo '-- logs'; journalctl --user -b --no-pager 2>/dev/null | grep -iE 'panel|docklike|picom' | tail -12; grep -iE 'panel|docklike|plugin' ~/.xsession-errors 2>/dev/null | tail -8; ls /usr/lib64/xfce4/panel/plugins/ 2>/dev/null | tr '\\n' ' '; echo; cat ~/.config/kiyu/backend ~/.config/kiyu/picom.log 2>&1 | head -5",
    "echo '=== desktop-diag'; xfdesktop --version 2>&1 | head -1; xrandr --listmonitors 2>&1 | head -4; xfconf-query -c xfce4-desktop -l -v 2>&1 | head -30; ls -la /usr/share/backgrounds/kiyu/ 2>&1; file /usr/share/backgrounds/kiyu/default.png 2>&1; python3 -c \"import gi; gi.require_version('GdkPixbuf','2.0'); from gi.repository import GdkPixbuf as G; p=G.Pixbuf.new_from_file('/usr/share/backgrounds/kiyu/default.png'); print('pixbuf', p.get_width(), p.get_height(), p.get_has_alpha(), p.get_bits_per_sample())\" 2>&1 | tail -1; journalctl --user -b --no-pager 2>/dev/null | grep -iE 'xfdesktop|backdrop|pixbuf' | tail -8; grep -iv 'dbind|Gtk-WARNING' ~/.xsession-errors 2>/dev/null | tail -10; ls ~/.cache/xfce4/desktop 2>&1 | head -3",
    "echo '=== wallpaper-diag'; ls -la /usr/share/backgrounds/ /usr/share/backgrounds/images/ 2>&1 | head -20; readlink -f /usr/share/backgrounds/images/default.png 2>&1; strings /usr/bin/xfdesktop | grep -i 'backgrounds\\|desktop-base' | head -3; xfconf-query -c xfce4-desktop -l -v 2>/dev/null | grep -i image",
    "echo '=== im'; im-config -m 2>&1 | head -3; cat /etc/xdg/autostart/org.fcitx.Fcitx5.desktop 2>&1 | head -12; env | grep -E 'IM_MODULE|XMODIFIERS'",
    "echo '=== flatpak'; flatpak remotes 2>/dev/null || echo none",
    "echo '=== disk'; df -h / /run/live/medium 2>/dev/null",
    "echo '=== END'",
]

# 2단계(phase=hangul): 한글 입력 검증 — 메모장을 띄워 한/영 키로 전환해 입력 (스크린샷으로 확인)
HANGUL = [
    "echo '=== hangul'; export XAUTHORITY=$HOME/.Xauthority; pgrep -x fcitx5 >/dev/null && echo 'fcitx5: running' || echo 'fcitx5: NOT running'; fcitx5-remote -n 2>&1; cat ~/.config/fcitx5/profile 2>&1 | head -5; env | grep -E 'IM_MODULE|XMODIFIERS'",
    "mousepad >/dev/null 2>&1 & sleep 5; w=$(xdotool search --classname mousepad 2>/dev/null | tail -1); echo \"mousepad window: $w\"; xdotool windowsize $w 760 320; xdotool windowmove $w 260 200; xdotool windowactivate --sync $w; sleep 1; xdotool type --delay 60 'abc '; xdotool key Hangul; sleep 0.5; echo -n 'after Hangul key: '; fcitx5-remote -n; xdotool type --delay 100 'gksrmf dlqfur xptmxm'; sleep 1; xdotool key Hangul; sleep 0.3; xdotool type --delay 60 ' end'; sleep 1; echo typed",
    "echo '=== END'",
]

# 3단계(phase=installer): 설치 프로그램(Anaconda) 을 띄워 브랜딩·언어 확인 (스크린샷)
INSTALLER = [
    "echo '=== installer'; export XAUTHORITY=$HOME/.Xauthority; w=$(xdotool search --classname mousepad 2>/dev/null | tail -1); [ -n \"$w\" ] && xdotool windowclose $w; cat /etc/anaconda/profile.d/kiyu.conf 2>&1 | head -6; cat /.buildstamp 2>&1 | head -4; ls -la /usr/share/anaconda/pixmaps/ 2>&1 | head -8",
    "sudo -E env DISPLAY=:0 XAUTHORITY=$HOME/.Xauthority /usr/bin/liveinst >/tmp/liveinst.log 2>&1 & sleep 60; ps -eo comm | grep -iE 'anaconda|liveinst' | sort | uniq -c; tail -5 /tmp/liveinst.log 2>/dev/null; sudo tail -5 /tmp/anaconda.log 2>/dev/null",
    "echo '=== END'",
]
PHASES = {"hangul": HANGUL, "installer": INSTALLER}

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(sock_path)
s.settimeout(1.0)
buf = b""
log = open(out_path, "wb")

def read_for(seconds):
    global buf
    end = time.time() + seconds
    while time.time() < end:
        try:
            chunk = s.recv(4096)
            if chunk:
                buf += chunk
                log.write(chunk); log.flush()
        except socket.timeout:
            pass

def send(text):
    s.sendall(text.encode())

def wait_for(pattern, seconds):
    global buf
    end = time.time() + seconds
    while time.time() < end:
        read_for(1)
        if re.search(pattern, buf[-4000:].decode(errors="replace")):
            return True
    return False

# 로그인
send("\n")
logged_in = False
for _ in range(8):
    if time.time() > deadline:
        break
    # 앞 단계에서 이미 로그인해 둔 셸(PS1 = 'SHELL> ')이면 바로 진행
    if wait_for(r"SHELL> $", 3):
        logged_in = True
        break
    if wait_for(r"login:", 10):
        send(USER + "\n")
        if wait_for(r"[Pp]assword:|비밀번호:|암호:", 8):
            send(PASSWORD + "\n")
        if wait_for(r"\$ ?$|\$ \r?\n?$", 10) or wait_for(r"live@", 5):
            logged_in = True
            break
    elif re.search(r"live@[^\s]*:[^$]*\$", buf[-2000:].decode(errors="replace")):
        logged_in = True
        break
    send("\n")

log.write(b"\n\n##### SERIAL SHELL: logged_in=%s\n" % str(logged_in).encode())
if logged_in:
    send("export PS1='SHELL> '; stty cols 200; export DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus\n")
    read_for(2)
    for cmd in PHASES.get(PHASE, COMMANDS):
        if time.time() > deadline:
            break
        send(cmd + "\n")
        wait_for(r"SHELL> $", 110 if PHASE else 25)
log.close()
sys.exit(0 if logged_in else 1)
