#!/usr/bin/env python3
"""QEMU 시리얼 콘솔(unix 소켓)로 라이브 세션에 로그인해 명령을 실행하고 결과를 저장합니다.
사용: serial-shell.py <socket> <output-file> [timeout-sec]
"""
import socket, sys, time, re

sock_path, out_path = sys.argv[1], sys.argv[2]
deadline = time.time() + float(sys.argv[3] if len(sys.argv) > 3 else 180)
USER, PASSWORD = "live", "live"
COMMANDS = [
    "echo '=== os-release'; cat /etc/os-release",
    "echo '=== uname'; uname -r",
    "echo '=== memory'; free -m",
    "echo '=== zram'; zramctl 2>/dev/null || echo none",
    "echo '=== top rss'; ps -eo rss,comm --sort=-rss | head -15",
    "echo '=== boot time'; systemd-analyze 2>/dev/null; systemd-analyze blame 2>/dev/null | head -12",
    "echo '=== failed units'; systemctl --failed --no-pager --no-legend",
    "echo '=== services'; for s in lightdm nftables apparmor zramswap unattended-upgrades NetworkManager; do printf '%s: %s\\n' $s $(systemctl is-active $s); done",
    "echo '=== firewall'; sudo nft list ruleset | head -30",
    "echo '=== apparmor'; sudo aa-status --json 2>/dev/null | head -c 400; echo",
    "echo '=== sysctl'; sysctl kernel.kptr_restrict kernel.yama.ptrace_scope kernel.unprivileged_bpf_disabled",
    "echo '=== cmdline'; cat /proc/cmdline",
    "echo '=== xsession'; ps -eo comm | grep -E '^(Xorg|lightdm|xfce4-session|xfwm4|xfce4-panel|xfdesktop|xcape|fcitx5)$' | sort | uniq -c",
    "echo '=== flatpak'; flatpak remotes 2>/dev/null || echo none",
    "echo '=== disk'; df -h / /run/live/medium 2>/dev/null",
    "echo '=== END'",
]

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
    if wait_for(r"login:", 10):
        send(USER + "\n")
        if wait_for(r"[Pp]assword:", 10):
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
    send("export PS1='SHELL> '; stty cols 200\n")
    read_for(2)
    for cmd in COMMANDS:
        if time.time() > deadline:
            break
        send(cmd + "\n")
        wait_for(r"SHELL> $", 25)
log.close()
sys.exit(0 if logged_in else 1)
