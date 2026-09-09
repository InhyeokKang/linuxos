# 빌드와 테스트

## 요구 사항

- Fedora (또는 `registry.fedoraproject.org/fedora:44` 컨테이너, `--privileged`).
- root 권한 (chroot, loop 장치 필요).
- 디스크 10 GB 이상, 인터넷 (Fedora 미러에서 약 2 GB 다운로드).

```bash
sudo dnf install kiwi-cli kiwi-systemdeps librsvg2-tools
```

0.1 의 Debian 이미지는 `BASE=debian sudo ./scripts/build.sh` 로 빌드합니다 (live-build 필요, `base/debian/`).

## 빌드

```bash
make check      # 정적 검사
make build      # = sudo ./scripts/build.sh
```

`base/fedora/out/build.log` 에 전체 로그가 남습니다. 결과물 (`base/fedora/out/`):

- `kiyu-1.0-x86_64.iso` – USB/DVD/VM 공용
- `kiyu-1.0-x86_64.iso.sha256`
- `kiyu-1.0-x86_64.iso.packages` – 포함된 패키지 목록

## ISO 없이 데스크톱 UI 만 보기

```bash
sudo ./scripts/preview-desktop.sh     # = make preview
```
Debian/Ubuntu 머신(컨테이너 가능)에 XFCE 와 kiyu 설정 트리를 올리고 Xvfb 에서 세션을 띄운 뒤
`out/preview/*.png` 로 스크린샷을 남깁니다. 패널/테마/단축키/메뉴 설정을 빠르게 반복 수정할 때 씁니다.
호스트 배포판의 XFCE 버전을 쓰므로 실제 ISO 와 세부 차이가 있을 수 있습니다.

## 테스트

```bash
make test               # QEMU, BIOS, 2 CPU / 2 GB
make test-uefi          # QEMU, UEFI (OVMF 필요: apt install ovmf)
./scripts/test-qemu.sh --ram 1024 --cpus 1     # 더 낮은 사양
./scripts/test-qemu.sh --uefi --disk           # 가상 디스크 붙여서 설치까지
```

설치 매체로 부팅하면 데스크톱 없이 곧바로 **Anaconda 설치 프로그램**이 뜹니다(`liveuser` 로 자동 로그인된 설치 전용 세션 `kiyu-installer`; `kiyu-live-installer.service` 가 lightdm 을 그 세션으로 돌립니다). 설치된 시스템에는 라이브 경로가 없어 평소 kiyu 데스크톱으로 부팅됩니다.

설치 프로그램을 닫으면 `installer-finished` 화면이 떠서 **재부팅 / 전원 끄기 / 설치 다시 하기** 중에 고르게 합니다. Anaconda 는 라이브 설치에서 마지막 버튼을 "재부팅"이 아니라 "설치 종료"로만 주고 그냥 종료하기 때문입니다(`conf.system.can_reboot` 이 라이브에서 거짓). 설치 완료 여부는 `/tmp/anaconda.log` 의 "The installation has finished" 로 판단해 기본 버튼을 정합니다.

### 자원 사용량 측정

라이브 세션 또는 설치본에서:

```bash
kiyu-info                               # 요약
free -m                                   # RAM
systemd-analyze                           # 부팅 시간
systemd-analyze blame | head -20          # 느린 서비스
ps -eo rss,comm --sort=-rss | head -15    # 메모리 많이 쓰는 프로세스
```

## 자주 겪는 문제

| 증상 | 원인/해결 |
|---|---|
| `No match for argument: ...` | 패키지 이름이 Fedora 에 없음. `dnf search` 로 확인 후 `kiyu.kiwi` 수정 |
| `KiwiInstallPhaseFailed` | 위 패키지 오류이거나 저장소 접근 문제. `base/fedora/out/build.log` 확인 |
| 빌드 중간 실패 후 재빌드 | `make clean` 후 다시 |
| ISO 는 되는데 그래픽 로그인이 안 뜸 | QEMU 에서 `-device virtio-vga` 사용 여부, `build.log` 의 lightdm 관련 오류 확인 |
| 한글 입력 안 됨 | 설치본에서 `imsettings-switch fcitx5` 후 재로그인 |
| 설치 중간에 "결점 보고" 크래시 창 | 킥스타트가 이미지에 없는 것을 요구함. `python3 scripts/lib/check-kickstart.py --rootfs <마운트한 rootfs>` 로 확인 (`make check` 는 빌드 전 근사 검사, `boot-test.sh` 는 빌드된 이미지로 정확히 검사) |

## 릴리스

버전은 **v1.0 고정**입니다. 숫자를 올리지 않고 같은 태그를 덮어씁니다.

1. 변경 사항을 `claude/lightweight-linux-os-1kbe9j` 에 푸시.
2. GitHub Actions > **Release kiyu ISO** 워크플로를 `tag: v1.0` 으로 수동 실행.
   ISO 빌드 → v1.0 릴리스의 `kiyu-1.0-x86_64.iso`, `SHA256SUMS.txt` 를 덮어씁니다.

## kiyu-desktop RPM

```sh
# Fedora 컨테이너 안에서
dnf -y install rpm-build gcc libX11-devel libXtst-devel python3 curl git
scripts/build-rpm.sh          # out/rpm/kiyu-desktop-<ver>-<n>.<sha>.fc44.x86_64.rpm
```
CI(`build-rpm.yml`)는 같은 스크립트로 빌드해 `kiyu-repo` 브랜치에 dnf 저장소를 올린다.
