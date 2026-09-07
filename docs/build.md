# 빌드와 테스트

## 요구 사항

- Debian 12 (bookworm) 이상 또는 `debian:trixie` 컨테이너. Ubuntu 도 되지만 live-build 버전이 오래돼서 권장하지 않습니다.
- root 권한 (chroot, mount 필요).
- 디스크 10 GB 이상, 인터넷 (Debian 미러에서 약 2 GB 다운로드; 두 번째 빌드부터는 `cache/` 재사용).

```bash
sudo apt-get install live-build debootstrap squashfs-tools xorriso librsvg2-bin
```

## 빌드

```bash
make check      # 정적 검사
make build      # = sudo ./scripts/build.sh
```

`build.log` 에 전체 로그가 남습니다. 결과물:

- `haneul-0.1.0-amd64.hybrid.iso` – USB/DVD/VM 공용
- `haneul-0.1.0-amd64.hybrid.iso.sha256`
- `haneul-0.1.0-amd64.packages` – 포함된 패키지 목록

## ISO 없이 데스크톱 UI 만 보기

```bash
sudo ./scripts/preview-desktop.sh     # = make preview
```
Debian/Ubuntu 머신(컨테이너 가능)에 XFCE 와 Haneul 설정 트리를 올리고 Xvfb 에서 세션을 띄운 뒤
`out/preview/*.png` 로 스크린샷을 남깁니다. 패널/테마/단축키/메뉴 설정을 빠르게 반복 수정할 때 씁니다.
호스트 배포판의 XFCE 버전을 쓰므로 실제 ISO 와 세부 차이가 있을 수 있습니다.

## 테스트

```bash
make test               # QEMU, BIOS, 2 CPU / 2 GB
make test-uefi          # QEMU, UEFI (OVMF 필요: apt install ovmf)
./scripts/test-qemu.sh --ram 1024 --cpus 1     # 더 낮은 사양
./scripts/test-qemu.sh --uefi --disk           # 가상 디스크 붙여서 설치까지
```

라이브 세션 로그인은 자동입니다 (사용자 `live`, 비밀번호 `live`). 바탕화면의 **Haneul OS 설치** 아이콘으로 Calamares 를 실행합니다.

### 자원 사용량 측정

라이브 세션 또는 설치본에서:

```bash
haneul-info                               # 요약
free -m                                   # RAM
systemd-analyze                           # 부팅 시간
systemd-analyze blame | head -20          # 느린 서비스
ps -eo rss,comm --sort=-rss | head -15    # 메모리 많이 쓰는 프로세스
```

## 자주 겪는 문제

| 증상 | 원인/해결 |
|---|---|
| `E: Unable to locate package ...` | 패키지 이름이 trixie 에 없음. `apt-cache search` 로 확인 후 목록 수정 |
| 훅에서 `nft -c` 실패 | `etc/nftables.conf` 문법 오류. 로컬에서 `nft -c -f` 로 재현 |
| 빌드 중간 실패 후 재빌드 | `sudo lb clean` 후 다시 (`cache/` 는 유지됨). 완전 초기화는 `make clean` |
| ISO 는 되는데 그래픽 로그인이 안 뜸 | QEMU 에서 `-device virtio-vga` 사용 여부, `build.log` 의 lightdm 관련 오류 확인 |
| 한글 입력 안 됨 | 설치본에서 `im-config -n fcitx5` 후 재로그인 |

## 릴리스

1. `os.conf` 의 `OS_VERSION` 올리기, `branding.desc` 의 버전 문자열 동기화.
2. `git tag v0.x.y && git push --tags`.
3. GitHub Actions > **Build ISO** 워크플로 수동 실행 → 산출물 다운로드 → Release 에 첨부.
