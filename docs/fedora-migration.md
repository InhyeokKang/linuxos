# Fedora 전환 기록

0.1 은 Debian 13 + live-build, 0.2 부터 Fedora + kiwi-ng 입니다. Debian 트리는 `base/debian/` 에 그대로 남아 있고 수동 워크플로(`Build ISO (Debian, legacy)`)로 빌드할 수 있습니다.

## 무엇이 바뀌었나

| 항목 | Debian (0.1) | Fedora (0.2) |
|---|---|---|
| 이미지 도구 | live-build | kiwi-ng (`base/fedora/kiyu.kiwi`, `config.sh`, `root/`) |
| 설치 프로그램 | Calamares | Anaconda (`liveinst`) |
| 라이브 사용자 | live-config (`live`/`live`) | livesys-scripts (`liveuser`, 비밀번호 없음) |
| MAC | AppArmor | SELinux (enforcing, targeted) |
| 방화벽 | nftables 직접 규칙 | firewalld, 기본 존 `kiyu` (target DROP) |
| 자동 보안 업데이트 | unattended-upgrades | dnf5-automatic (`upgrade_type = security`) |
| zram | zram-tools | zram-generator (RAM 50%, 최대 4 GB, zstd) |
| 커널 파라미터 | live-build bootappend + grub.d | kiwi kernelcmdline + 첫 부팅 시 grubby 로 설치본 BLS 항목에 추가 |
| 세션 환경 | /etc/X11/Xsession.d | /etc/X11/xinit/xinitrc.d |
| Super 탭 | xcape (Debian 패키지) | kiyu-superkey (자체 C 구현, 빌드 시 컴파일) |
| 기본 브라우저 | Firefox ESR | kiyu 브라우저 (WebKitGTK) |
| 코덱/NVIDIA | Debian non-free | RPM Fusion (게임 설정 스크립트가 필요 시 추가) |

동일하게 유지된 것: XFCE 윈도우 배치와 단축키(`/etc/xdg/xdg-kiyu`), 테마·폰트·한글 입력기, 배경화면 교체 방식, 패널 플러그인 in-process, 도우미 스크립트, 부팅 테스트 파이프라인.

## 알아둘 것

- Fedora 는 13개월 지원입니다. 6개월마다 새 릴리스로 이미지를 다시 빌드하고 설치본은 `dnf system-upgrade` 로 올려야 합니다. 로드맵에 "릴리스 업그레이드 도우미" 가 있습니다.
- 라이브 세션은 SELinux 가 enforcing 이지만 livesys 가 일부 완화합니다. 설치본에서 정상 정책이 적용됩니다.
- 미디어 코덱(H.264 등)은 Fedora 공식 저장소에 없습니다. `kiyu-setup-gaming` 처럼 필요 시 RPM Fusion 을 붙이는 스크립트를 0.2 에서 추가합니다.
