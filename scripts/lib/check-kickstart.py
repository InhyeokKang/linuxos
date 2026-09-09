#!/usr/bin/env python3
"""킥스타트 <-> 이미지 패키지 정합성 검사.

Anaconda 킥스타트가 요구하는데 이미지에 없는 패키지를 잡는다.
실제 사고: firewall --enabled 인데 firewalld 를 빼서, 설치 마무리 단계에
FirewallConfigurationError 로 크래시했다("결점 보고" 창).
"""
import re
import sys

KS = "base/fedora/root/usr/share/anaconda/interactive-defaults.ks"
KIWI = "base/fedora/kiyu.kiwi"

# systemd 유닛 -> 그 유닛을 제공하는 패키지
UNIT_PKG = {
    "NetworkManager": "NetworkManager",
    "chronyd": "chrony",
    "nftables": "nftables",
    "sshd": "openssh-server",
    "firewalld": "firewalld",
    "lightdm": "lightdm",
}


def main():
    try:
        ks_text = open(KS, encoding="utf-8").read()
        kiwi_text = open(KIWI, encoding="utf-8").read()
    except OSError:
        return 0  # 파일이 없으면 이 검사는 건너뛴다

    pkgs = set(re.findall(r'<package name="([^"]+)"', kiwi_text))
    # kiwi 의 delete/uninstall 로 제거되는 패키지는 최종 이미지에 없다
    removed = set()
    for block in re.findall(r'<packages type="(?:delete|uninstall)">(.*?)</packages>', kiwi_text, re.S):
        removed |= set(re.findall(r'<package name="([^"]+)"', block))
    pkgs -= removed

    ok = True
    for raw in ks_text.splitlines():
        line = raw.strip()
        if line.startswith("#") or not line:
            continue

        # firewall --enable/--enabled 는 대상 시스템에 firewalld(firewall-offline-cmd)가 있어야 한다
        if line.startswith("firewall ") and re.search(r"--enabled?\b", line):
            if "firewalld" not in pkgs:
                print("FAIL: 'firewall --enabled' 는 firewalld 가 필요한데 kiyu.kiwi 에 없습니다.")
                print("      nftables 를 쓰면 'firewall --use-system-defaults' 로 두세요.")
                ok = False

        # services --enabled=... 의 유닛을 제공하는 패키지가 이미지에 있어야 한다
        if line.startswith("services ") and "--enabled=" in line:
            units = line.split("--enabled=", 1)[1].split()[0]
            for unit in units.split(","):
                need = UNIT_PKG.get(unit.strip())
                if need and need not in pkgs:
                    print(f"FAIL: services --enabled={unit.strip()} 인데 {need} 패키지가 kiyu.kiwi 에 없습니다.")
                    ok = False

        # 암호화 autopart 는 cryptsetup 이 필요하다
        if line.startswith("autopart") and "--encrypted" in line and "cryptsetup" not in pkgs:
            print("FAIL: autopart --encrypted 인데 cryptsetup 이 kiyu.kiwi 에 없습니다.")
            ok = False

        # btrfs 스킴은 btrfs-progs 가 필요하다
        if line.startswith("autopart") and "btrfs" in line and "btrfs-progs" not in pkgs:
            print("FAIL: autopart --type=btrfs 인데 btrfs-progs 가 kiyu.kiwi 에 없습니다.")
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
