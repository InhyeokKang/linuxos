# 보안 설계

"보안이 뛰어나다"를 실제로 만드는 것은 하나의 기능이 아니라 **기본값으로 켜져 있는 여러 겹**입니다. 일반 사용자가 설정을 만지지 않아도 아래 전부가 동작합니다.

## 계층

| 계층 | 구현 | 파일 |
|---|---|---|
| 부팅 | Secure Boot (Debian 서명 shim/GRUB/커널), 커널 lockdown | live-build `--uefi-secure-boot`, `shim-signed` |
| 디스크 | LUKS 전체 디스크 암호화 (설치 시 체크박스 하나) | `calamares/modules/partition.conf` |
| 커널 | kptr/dmesg 제한, 비특권 BPF 차단, ptrace 제한, ASLR 최대, `init_on_alloc`, `slab_nomerge`, `randomize_kstack_offset` | `etc/sysctl.d/90-kiyu-hardening.conf`, `etc/default/grub.d/10-kiyu.cfg` |
| 커널 모듈 | 안 쓰는 네트워크 프로토콜/파일시스템/FireWire 로드 차단 | `etc/modprobe.d/10-kiyu-blacklist.conf` |
| 네트워크 | firewalld 기본 존 `kiyu` (인바운드 전부 DROP), IPv4/6 리다이렉트·소스라우팅 무시, SYN 쿠키 | `etc/firewalld/zones/kiyu.xml`, sysctl |
| MAC | SELinux enforcing (targeted) | Fedora 기본, kiwi 빌드 시 relabel |
| 앱 격리 | Flatpak(bubblewrap) 샌드박스 + 포털; 브라우저 웹 프로세스도 bubblewrap 샌드박스 | `xdg-desktop-portal/portals.conf`, `apps/kiyu-browser` |
| 브라우저 | 추적 방지(ITP), 서드파티 쿠키·추적기 차단, 권한 기본 거부, HTTPS 우선 | [browser.md](browser.md) |
| 업데이트 | 보안 업데이트 매일 자동 설치(dnf5-automatic), 재부팅은 사용자 선택 | `etc/dnf/automatic.conf` |
| 펌웨어 | fwupd (LVFS) 로 BIOS/SSD 펌웨어 업데이트 | `10-hardware.list.chroot` |
| 계정 | root 잠금, sudo 는 비밀번호 필요, 홈 디렉터리 0700, 게스트 로그인 없음 | 하드닝 훅, `lightdm.conf.d` |
| 화면 | 10분 유휴 시 화면 잠금, 절전 복귀 시 잠금 | `xfce4-screensaver.xml`, `xfce4-power-manager.xml` |
| 프라이버시 | 텔레메트리 없음, geoip 조회 없음, mDNS/avahi 없음 | 설치 프로그램·패키지 선택 |
| 시간 | systemd-timesyncd (NTP) | `00-core.list.chroot` |

## 의도적으로 *하지 않은* 것 (호환성 트레이드오프)

- `kernel.unprivileged_userns_clone=0`: Flatpak, Chrome/Firefox 샌드박스, Steam 이 사용자 네임스페이스를 씁니다. 끄면 앱이 안 돕니다.
- `ptrace_scope=2/3`: 디버거, Steam 오버레이, 일부 게임 안티치트 대응이 깨집니다. `1`(자식 프로세스만)로 둡니다.
- USBGuard: 새 키보드/마우스를 꽂을 때마다 승인해야 해서 일반 사용자에게 과합니다. 로드맵의 "고급 보안 프로필" 옵션으로.
- 방화벽에서 mDNS(5353) 차단: 네트워크 프린터 자동 검색이 안 됩니다. IP 로 추가하거나 `/etc/nftables.d/` 예시 주석을 풀면 됩니다.
- LUKS1 기본: GRUB 이 `/boot` 를 해독해야 하는 구성에서 LUKS2 argon2 는 GRUB 버전에 따라 부팅이 안 될 수 있어 검증된 LUKS1 을 씁니다. `/boot` 를 별도 파티션으로 두는 수동 파티셔닝에서는 LUKS2 사용 가능.
- `mitigations=auto`(기본값) 유지: CPU 취약점 완화를 끄면 빨라지지만 보안 목표와 어긋납니다.

## 라이브 세션과 설치본의 차이

라이브 세션은 livesys 가 편의를 위해 일부 정책(자동 로그인, 비밀번호 없는 sudo)을 완화합니다. 디스크에 설치한 뒤에는 정상 정책이 적용됩니다.
(0.1 Debian 이미지에서는 `apparmor.service` 가 라이브 overlay 조건 때문에 inactive 였습니다. 같은 이유의 라이브 전용 완화입니다.)

## 사용자가 확인하는 방법

```
kiyu-info
```
방화벽/AppArmor/자동 업데이트/Secure Boot/디스크 암호화 상태를 한 번에 보여 줍니다.

## 포트 열기

```
sudo firewall-cmd --permanent --add-port=27036/tcp     # 예: Steam 원격 플레이
sudo firewall-cmd --reload
```
