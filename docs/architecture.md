# 설계 근거

## 목표를 숫자로

| 항목 | 목표 | 비교 (Windows 11) |
|---|---|---|
| 유휴 RAM | ≤ 500 MB (데스크톱 로그인 직후) | 2.5~4 GB |
| 최소 사양 | 2 GB RAM, 듀얼코어 x86-64, 16 GB 디스크 | 4 GB, TPM 2.0, 64 GB |
| 부팅 | 전원 → 로그인 화면 15초 이내 (SSD) | 20~40초 |
| 설치 용량 | ≤ 6 GB (오피스 포함) | 25~30 GB |
| ISO | ≤ 2.2 GB | 5+ GB |
| 유휴 CPU | < 1% | 2~5% (텔레메트리, 인덱싱, 업데이트 서비스) |
| GPU | 컴포지터만 (2D) | DWM 이 항상 3D 가속 사용 |

## 핵심 결정

### 1. 베이스: 0.1 은 Debian, 0.2 부터 Fedora

0.1 은 아래 이유로 Debian stable 을 골랐고, 0.2 에서 최신 하드웨어 지원과 SELinux 등 강한 보안 기본값을 우선해 Fedora 로 전환했습니다 (비교는 [fedora-migration.md](fedora-migration.md)). 13개월 지원 주기는 릴리스 업그레이드 도우미로 대응합니다.

#### 0.1 에서 Debian 을 고른 이유

- **보안 업데이트가 보장된다.** Debian 보안팀이 5년간 패치. 자동 보안 업데이트를 켜 두면 사용자가 신경 쓸 게 없다.
- **glibc.** Alpine(musl) 은 더 가볍지만 Steam, Wine, 상용 앱, NVIDIA 드라이버가 사실상 안 된다. "게임과 프로그램 설치에 제약이 없어야 한다"는 요구와 충돌한다.
- **stable 이라 갑자기 깨지지 않는다.** Arch 는 롤링이라 일반 사용자에게 위험하다.
- **Ubuntu 대비**: snap 강제, 서드파티 텔레메트리, 무거운 기본 서비스가 없다. 최신 하드웨어는 `trixie-backports` 커널로 커버.
- **live-build** 로 ISO 를 재현 가능하게 만들 수 있다 (Debian 공식 라이브 이미지와 같은 도구).

### 1b. 브라우저: 엔진은 WebKitGTK, 브라우저는 kiyu

Firefox/Chrome 대신 kiyu 가 직접 만든 브라우저를 기본으로 씁니다. 엔진을 새로 만드는 것은 불가능에 가깝고, 엔진 위의 브라우저(UI·정책·차단·권한)를 만드는 것이 정석입니다. 근거와 설계는 [browser.md](browser.md).

### 2. 왜 XFCE 인가 (KDE, GNOME, LXQt 가 아니라)

| DE | 유휴 RAM | GPU 의존 | 윈도우 유사도 | 안정성 |
|---|---|---|---|---|
| GNOME | 800 MB~ | 높음 (Mutter) | 낮음 | 높음 |
| KDE Plasma 6 | 600~900 MB | 높음 (KWin) | 매우 높음 | 중간 |
| **XFCE 4.20** | **250~350 MB** | **매우 낮음** | 높음 (설정으로) | **매우 높음** |
| LXQt 2 | 200~300 MB | 낮음 | 중간 | 중간 |

KDE 가 가장 윈도우 같지만 저사양 목표와 충돌한다. XFCE 는 패널·단축키·테마만 바꾸면 윈도우 10 배치가 되고(Zorin Lite, Linux Lite 가 같은 접근), 15년 넘게 안정적이다. LXQt 는 조금 더 가볍지만 Qt 앱 생태계와 문서가 부족해서 0.1 에서는 XFCE 를 고른다.

기본 설정은 `/etc/xdg/xdg-kiyu/` 에 두고, 세션 래퍼(`startkiyu`)가 `XDG_CONFIG_DIRS` 맨 앞에 붙인다. 그래서 XFCE 패키지의 기본 설정 파일을 덮어쓰지 않아 업그레이드 충돌이 없고, 사용자 설정은 늘 우선한다.

### 3. X11 vs Wayland

0.1 은 X11. 이유는 (1) XFCE 4.20 의 Wayland 지원이 아직 실험적이고, (2) 저사양 GPU 에서 X11 + xfwm4 컴포지터가 가장 검증됐으며, (3) Wine/Steam 호환성이 X11 에서 가장 좋다. Wayland 전환은 XFCE 4.22 이후 로드맵.

### 4. 앱 설치: 세 갈래

1. **Flatpak (Flathub)** – 기본 경로. 앱 스토어 UX, bubblewrap 샌드박스, 최신 버전. Steam/Discord/Chrome/카카오톡(Wine) 등 대부분.
2. **apt (.deb)** – 시스템 도구, 드라이버. `.deb` 더블클릭은 GNOME Software 가 처리.
3. **Wine / Bottles** – `.exe`. 선택 설치.

Recommends 를 끄고 빌드하므로(`--apt-recommends false`) 이미지가 작다. 대신 설치본에서 사용자가 `apt install` 할 때는 Debian 기본값(Recommends 설치)이 그대로라 "뭔가 빠져서 안 되는" 일이 없다.

### 5. 용량과 메모리를 어디서 줄였나

- `debootstrap --variant=minbase` + Recommends 없음 → 필요한 것만 명시적으로 나열.
- dpkg `path-exclude` 로 man/doc/info, 한국어·영어 외 번역 미설치 (`01-kiyu-lean`).
- squashfs zstd 압축: xz 보다 저사양 CPU 에서 라이브 부팅이 훨씬 빠름.
- zram 스왑(zstd, RAM 50%) + `vm.swappiness=150`: 2 GB 머신에서 브라우저 탭 여러 개가 버팀. 디스크 스왑 파일은 설치 시 선택.
- 서비스 최소화: rsyslog/cron/avahi/ModemManager 없음. journald + systemd 타이머로 충분.
- 컴포지터는 켜되 그림자 끔: 티어링 방지(윈도우 사용자가 가장 먼저 느끼는 이질감)와 GPU 부하의 타협.
- Plymouth(부팅 스플래시) 없음: 1~2초와 수십 MB 절약.

### 5b. 룩앤필: 사양을 먹지 않는 "트렌디"

- **배경**: 크림 종이 위 파스텔 곡선(새벽 언덕)과 귤 단면 로고. 정적 PNG 한 장이라 비용 0.
- **독**: 가운데 떠 있는 독은 Plank (`plank` 패키지, `/etc/dconf/db/local.d/00-kiyu-plank`, 테마 `/usr/share/plank/themes/kiyu{,-dark}`).
  고정 앱 + 실행 중 창을 한 아이콘으로, 실행 중이면 아래 점 (윈도우 작업표시줄과 같은 동작). 첫 아이콘(kiyu 로고)이 시작 메뉴.
  xfce4-panel 은 화면 가장자리에서 띄우는 기능이 없어 독으로 쓰지 않는다. Plank 는 약 30~50 MB 상주.
- **작업표시줄 알약**: 오른쪽 아래 xfce4-panel 하나 (트레이·빠른 설정·시계·알림·바탕화면 보기). whiskermenu 플러그인은
  버튼을 숨긴 채 팝업 전용으로 들어 있다 (`xfce4-popup-whiskermenu --pointer` 가 독의 로고 클릭과 Super 키에서 호출).
  배경은 xfconf 가 아니라 `~/.config/gtk-3.0/gtk.css` 의 `.xfce4-panel` 이 그려서 테마 색(다크 모드)을 따라간다.
  Plank 는 이 알약이 예약한 공간 위에 놓이므로 자연스럽게 바닥에서 떠 있다.
- **창**: xfwm4 자체 컴포지팅 대신 picom(xrender) — 둥근 모서리 12px, 부드러운 그림자, 짧은 페이드. CPU 1~3%.
  유리 블러(glx, dual_kawase)는 GPU 없는 기기에서 비싸므로 기본 OFF, 빠른 설정 "효과" 스위치로 켠다 (`/usr/lib/kiyu/compositor`).
- **빠른 설정** (`apps/kiyu-control`): Wi-Fi/블루투스/다크 모드/효과 토글, 소리·밝기, 배터리. 상주하지 않는 Python GTK 창(열려 있을 때만 ~20 MB).
  소리·전원 패널 애플릿을 대체했고 볼륨 키는 `/usr/lib/kiyu/volume` + OSD 알림이 맡는다.
- **다크 모드** (`/usr/lib/kiyu/theme`): Adwaita ↔ Adwaita-dark, Papirus ↔ Papirus-Dark, 패널 dark-mode 를 한 번에. gtk.css 는 `@theme_*` 색을 섞어 쓰므로 재시작 없이 따라온다.
- **폰트**: Pretendard → IBM Plex Sans KR → Inter → 본고딕 순 대체 체인.

### 6. 윈도우 사용자 경험

- 하단 패널: [시작][탐색기][브라우저][실행 중 창들] … [트레이][소리][전원][시계][알림][바탕화면 보기]
- 시작 메뉴(Whisker): 검색창 위, 즐겨찾기, 전원 버튼 하단.
- 단축키: `docs/windows-user-guide.md` 참조. `Super` 를 혼자 눌렀다 떼면 시작 메뉴 (xcape 가 Alt+F1 로 변환). Super_L 을 xfsettingsd 에 직접 바인딩하면 xfwm4 의 Super+화살표 단축키가 죽기 때문에 이 방식을 쓴다.
- 창: 제목 왼쪽 정렬, 최소화/최대화/닫기 오른쪽, 더블클릭 최대화, 가장자리 드래그 스냅(Aero Snap), 작업공간 1개.
- 바탕화면 아이콘: 내 컴퓨터(파일시스템), 홈, 휴지통, 이동식 드라이브.
- 폰트: 맑은 고딕/Segoe UI/Arial/Calibri 요청 시 동일 규격 대체 폰트로 자동 매핑 (fontconfig).
- 관리자 권한(UAC): polkit 에이전트가 비밀번호 창을 띄움. root 직접 로그인은 잠금.
- Ctrl+Alt+Del 콘솔 재부팅은 mask, 데스크톱에서는 작업 관리자.

## 디렉터리 흐름 (live-build)

```
lb config  ─► auto/config 가 os.conf 를 읽어 config/* 생성
lb build   ─► debootstrap(minbase)
           ─► includes.chroot_before_packages 복사 (dpkg 용량 설정)
           ─► package-lists/*.list.chroot 설치
           ─► includes.chroot_after_packages 복사 (시스템 설정, 브랜딩)
           ─► hooks/normal/*.hook.chroot 실행 (os-release, 서비스, PNG 생성, 정리)
           ─► squashfs (zstd) + 커널/initrd + 부트로더 ─► hybrid ISO
```
