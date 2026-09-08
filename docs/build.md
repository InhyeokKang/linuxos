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

- `kiyu-0.2.0-x86_64.iso` – USB/DVD/VM 공용
- `kiyu-0.2.0-x86_64.iso.sha256`
- `kiyu-0.2.0-x86_64.iso.packages` – 포함된 패키지 목록

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

라이브 세션 로그인은 자동입니다 (사용자 `liveuser`, 비밀번호 없음). 바탕화면의 **kiyu 설치** 아이콘으로 Anaconda 를 실행합니다.

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

## 릴리스

1. `os.conf` 의 `OS_VERSION` 올리기.
2. `git tag v0.x.y && git push --tags`.
3. GitHub Actions > **Build ISO** 워크플로 수동 실행 → 산출물 다운로드 → Release 에 첨부.

## kiyu-desktop RPM

```sh
# Fedora 컨테이너 안에서
dnf -y install rpm-build gcc libX11-devel libXtst-devel python3 curl git
scripts/build-rpm.sh          # out/rpm/kiyu-desktop-<ver>-<n>.<sha>.fc44.x86_64.rpm
```
CI(`build-rpm.yml`)는 같은 스크립트로 빌드해 `kiyu-repo` 브랜치에 dnf 저장소를 올린다.
