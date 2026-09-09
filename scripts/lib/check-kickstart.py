#!/usr/bin/env python3
"""킥스타트 <-> 이미지 정합성 검사.

Anaconda 킥스타트가 요구하는데 이미지에 없는 것을 잡는다.
실제 사고: firewall --enabled 인데 firewalld 를 빼서, 설치 마무리 단계에
FirewallConfigurationError 로 크래시했다("결점 보고" 창).

두 가지 모드가 있다.

  (기본) 빌드 전  : kiyu.kiwi 의 패키지 목록으로 검사한다. 빠르지만 의존성으로
                    딸려 오는 패키지는 모르므로 근사치다.
  --rootfs DIR   : 빌드 후, 실제 루트 트리(ISO 안의 rootfs)로 검사한다.
                    라이브 설치는 이 트리를 그대로 대상 시스템에 복사하므로,
                    여기에 없는 바이너리/유닛은 설치 중에도 없다. 정확하다.

`--rootfs` 검사 대상은 Anaconda 44 의 설치 태스크를 실제로 읽어서 뽑았다.
설치 중 sysroot 안에서 실행되거나 존재를 확인하는 것들이다.
"""
import argparse
import os
import re
import sys

# 어디서 실행하든(CI 의 boot-test 포함) 저장소 기준으로 찾는다
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KS = os.path.join(REPO, "base/fedora/root/usr/share/anaconda/interactive-defaults.ks")
KIWI = os.path.join(REPO, "base/fedora/kiyu.kiwi")

# systemd 유닛 -> 그 유닛을 제공하는 패키지 (빌드 전 검사용)
UNIT_PKG = {
    "NetworkManager": "NetworkManager",
    "chronyd": "chrony",
    "nftables": "nftables",
    "sshd": "openssh-server",
    "firewalld": "firewalld",
    "lightdm": "lightdm",
}

# Anaconda 가 설치 도중 대상 시스템 안에서 실행하는 도구들.
# (pyanaconda 의 execInSysroot/execWithRedirect 호출을 훑어서 x86 경로에 해당하는 것만 추렸다)
ALWAYS_NEED = [
    ("rsync", "라이브 파일시스템 복사(InstallFromImageTask)"),
    ("systemctl", "서비스 활성화/기본 타겟 설정"),
    ("useradd", "사용자 생성"),
    ("groupadd", "그룹 생성"),
    ("chage", "암호 만료 설정"),
    ("authselect", "인증 설정(ConfigureAuthselectTask)"),
    ("dracut", "initramfs 재생성"),
    ("grub2-install", "BIOS 부트로더 설치"),
    ("grub2-mkconfig", "부트로더 설정 생성"),
    ("efibootmgr", "UEFI 부트 항목 등록"),
    ("mount", "대상 파일시스템 마운트"),
    ("umount", "대상 파일시스템 해제"),
    ("findmnt", "마운트 확인"),
    ("lsblk", "블록 장치 조회"),
]

BIN_DIRS = ("usr/bin", "usr/sbin", "bin", "sbin")
UNIT_DIRS = ("usr/lib/systemd/system", "etc/systemd/system", "usr/local/lib/systemd/system")


def read_ks():
    with open(KS, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]


def ks_value(lines, cmd):
    for line in lines:
        if line.split()[:1] == [cmd]:
            return line
    return None


# ---------------------------------------------------------------- 빌드 전


def check_kiwi(lines):
    with open(KIWI, encoding="utf-8") as f:
        kiwi_text = f.read()
    pkgs = set(re.findall(r'<package name="([^"]+)"', kiwi_text))
    # kiwi 의 delete/uninstall 로 제거되는 패키지는 최종 이미지에 없다
    for block in re.findall(r'<packages type="(?:delete|uninstall)">(.*?)</packages>', kiwi_text, re.S):
        pkgs -= set(re.findall(r'<package name="([^"]+)"', block))

    ok = True
    for line in lines:
        # firewall --enable/--enabled 는 대상 시스템에 firewalld(firewall-offline-cmd)가 있어야 한다
        if line.startswith("firewall ") and re.search(r"--enabled?\b", line):
            if "firewalld" not in pkgs:
                print("FAIL: 'firewall --enabled' 는 firewalld 가 필요한데 kiyu.kiwi 에 없습니다.")
                print("      nftables 를 쓰면 'firewall --use-system-defaults' 로 두세요.")
                ok = False

        # services --enabled=... 의 유닛을 제공하는 패키지가 이미지에 있어야 한다
        if line.startswith("services ") and "--enabled=" in line:
            for unit in line.split("--enabled=", 1)[1].split()[0].split(","):
                need = UNIT_PKG.get(unit.strip())
                if need and need not in pkgs:
                    print(f"FAIL: services --enabled={unit.strip()} 인데 {need} 패키지가 kiyu.kiwi 에 없습니다.")
                    ok = False

        if line.startswith("autopart"):
            # 암호화 autopart 는 cryptsetup, btrfs 스킴은 btrfs-progs 가 필요하다
            if "--encrypted" in line and "cryptsetup" not in pkgs:
                print("FAIL: autopart --encrypted 인데 cryptsetup 이 kiyu.kiwi 에 없습니다.")
                ok = False
            if "btrfs" in line and "btrfs-progs" not in pkgs:
                print("FAIL: autopart --type=btrfs 인데 btrfs-progs 가 kiyu.kiwi 에 없습니다.")
                ok = False
    return ok


# ---------------------------------------------------------------- 빌드 후


class Root:
    def __init__(self, path):
        self.path = path.rstrip("/")

    def has(self, rel):
        return os.path.lexists(os.path.join(self.path, rel.lstrip("/")))

    def which(self, name):
        for d in BIN_DIRS:
            p = os.path.join(self.path, d, name)
            if os.path.lexists(p):
                return p
        return None

    def unit(self, name):
        """유닛 파일 경로를 돌려준다. masked(=/dev/null 심볼릭 링크)면 'masked'."""
        if not name.endswith(".service") and "." not in name:
            name += ".service"
        for d in UNIT_DIRS:
            p = os.path.join(self.path, d, name)
            if os.path.lexists(p):
                if os.path.islink(p) and os.readlink(p) == "/dev/null":
                    return "masked"
                return p
        return None


def check_rootfs(lines, root):
    ok = True

    def fail(msg, why=""):
        nonlocal ok
        print(f"FAIL: {msg}")
        if why:
            print(f"      {why}")
        ok = False

    for name, why in ALWAYS_NEED:
        if not root.which(name):
            fail(f"{name} 이(가) 이미지에 없습니다.", f"Anaconda 가 설치 중 씁니다: {why}")

    for line in lines:
        if line.startswith("firewall "):
            # ConfigureFirewallTask: --enabled 인데 firewall-offline-cmd 가 없으면 크래시한다
            if re.search(r"--enabled?\b", line) and not root.has("usr/bin/firewall-offline-cmd"):
                fail("'firewall --enabled' 인데 /usr/bin/firewall-offline-cmd 가 없습니다.",
                     "설치 마무리에서 FirewallConfigurationError 로 크래시합니다. "
                     "nftables 를 쓰면 'firewall --use-system-defaults' 로 두세요.")

        if line.startswith("services ") and "--enabled=" in line:
            # ConfigureServicesTask 는 systemctl enable 이 실패하면 ValueError 를 던진다
            for unit in line.split("--enabled=", 1)[1].split()[0].split(","):
                unit = unit.strip()
                found = root.unit(unit)
                if found is None:
                    fail(f"services --enabled={unit} 인데 유닛 파일이 이미지에 없습니다.",
                         "systemctl enable 이 실패해 설치가 크래시합니다.")
                elif found == "masked":
                    fail(f"services --enabled={unit} 인데 유닛이 masked 되어 있습니다.",
                         "systemctl enable 이 실패해 설치가 크래시합니다.")

        if line.startswith("autopart"):
            if "--encrypted" in line and not root.which("cryptsetup"):
                fail("autopart --encrypted 인데 cryptsetup 이 없습니다.")
            if "btrfs" in line and not root.which("mkfs.btrfs"):
                fail("autopart --type=btrfs 인데 mkfs.btrfs 가 없습니다.")

        if line.startswith("selinux ") and "--enforcing" in line:
            if not root.which("restorecon"):
                fail("selinux --enforcing 인데 restorecon 이 없습니다.", "policycoreutils 필요")
            if not root.has("etc/selinux/targeted"):
                fail("selinux --enforcing 인데 /etc/selinux/targeted 가 없습니다.",
                     "selinux-policy-targeted 필요")

        if line.startswith("timezone "):
            tz = [w for w in line.split()[1:] if not w.startswith("--")]
            if tz and not root.has("usr/share/zoneinfo/" + tz[0]):
                fail(f"timezone {tz[0]} 인데 /usr/share/zoneinfo/{tz[0]} 가 없습니다.", "tzdata 필요")

        if line.startswith("keyboard ") and "--xlayouts=" in line:
            layouts = line.split("--xlayouts=", 1)[1].split()[0].strip("'\"")
            for lay in layouts.split(","):
                lay = lay.split("(")[0].strip("'\" ")
                if lay and not root.has("usr/share/X11/xkb/symbols/" + lay):
                    fail(f"keyboard --xlayouts={lay} 인데 xkb 심볼 파일이 없습니다.",
                         "xkeyboard-config 필요")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rootfs", help="빌드된 루트 트리 경로 (마운트된 rootfs.img)")
    args = ap.parse_args()

    try:
        lines = read_ks()
    except OSError:
        return 0  # 킥스타트가 없으면 이 검사는 건너뛴다

    if args.rootfs:
        return 0 if check_rootfs(lines, Root(args.rootfs)) else 1
    try:
        return 0 if check_kiwi(lines) else 1
    except OSError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
