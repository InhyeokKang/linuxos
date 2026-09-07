# 로드맵

## 0.2 – Fedora + kiyu 룩 (진행 중)

- [x] Fedora 44 + kiwi-ng 라이브 ISO, BIOS/UEFI(Secure Boot) 부팅, SELinux enforcing, nftables
- [x] 탱자 브라우저 (WebKitGTK), Super 키 시작 메뉴, docklike 작업표시줄
- [x] 새벽 배경 + 가운데 정렬 작업표시줄 + picom 둥근 창 + 빠른 설정(다크 모드·효과) — Xvfb 프리뷰 검증, ISO 검증 대기
- [ ] 실제 ISO 에서 picom/빠른 설정/docklike 확인, 메모리 재측정
- [ ] 바탕화면 시계·달력 위젯(선택), 통합 검색 런처

## 0.1 – 스캐폴드 (현재)

설정 트리, 정적 검사, 문서 완료. 데스크톱 UI 는 `scripts/preview-desktop.sh` (Xvfb) 로 검증했고
결과는 `docs/screenshots/` 에 있습니다. **ISO 빌드/부팅은 아직 미검증.**

Xvfb 프리뷰에서 확인된 것:

- [x] `/etc/xdg/xdg-kiyu` 오버라이드 트리가 xfconf 에 병합됨 (패널, 테마, 창 관리자, 단축키)
- [x] 패널 launcher 플러그인이 절대 경로 `.desktop` 항목을 받아들임
- [x] Whisker 시작 메뉴 즐겨찾기/세션 버튼, Ctrl+Shift+Esc 작업 관리자, Win+E 탐색기, Win+←/→ 창 스냅, Alt+F4
- [x] 기본 배경화면: xfdesktop 기본 배경 파일을 dpkg-divert 로 교체 (모니터 이름과 무관하게 첫 로그인부터 적용)
- [x] `mate-polkit` 에이전트 경로 자동 탐색
- [x] 발견한 버그 수정: `librsvg2-common` (SVG 아이콘/배경 로더) 누락, Super 단독 바인딩이 Super+화살표를 가로채는 문제 → xcape 로 해결, XDG_CONFIG_DIRS 가 D-Bus 활성화 데몬에 전달되지 않던 문제 → Xsession.d 스크립트 추가

첫 ISO 빌드에서 확인할 것:

- [ ] 모든 패키지 이름이 trixie 에 존재하는지 (`E: Unable to locate package`), 특히 `xcape`, `7zip`, `fcitx5-frontend-qt6`
- [ ] live-build 버전이 `includes.chroot_before_packages` 를 지원하는지 (bookworm 1:20230502 이상)
- [ ] `--uefi-secure-boot auto` 로 Secure Boot 켠 VM 에서 부팅
- [ ] 라이브 자동 로그인, 한글 입력 (fcitx5)
- [ ] 실제 키보드에서 Win 키 탭 → 시작 메뉴 (xcape; Xvfb 의 합성 키 입력으로는 검증 불가), Win+D 바탕화면 보기
- [ ] Calamares: 모듈 이름/설정 키가 trixie 의 3.3.x 와 맞는지, BIOS/UEFI 설치, LUKS 설치, 윈도우 듀얼부팅 감지
- [ ] 설치 후 `live` 사용자 제거, 설치 아이콘 제거, `kiyu-firstboot` 재실행
- [ ] 유휴 RAM 측정 → README 수치 갱신 (Xvfb 프리뷰에서 데스크톱 프로세스 PSS 합계 약 250 MB)

## 0.2 – Fedora 전환 + 탱자 브라우저 (진행 중)

- [x] Fedora 44 kiwi 이미지 정의, kiwi 스키마 검증, CI 컨테이너 빌드
- [x] 탱자 브라우저 v0 (WebKitGTK): 탭·주소창·검색·즐겨찾기·다운로드, 샌드박스·ITP·추적기 차단·권한 기본 거부
- [x] kiyu-superkey (Super 탭 → 시작 메뉴, Super+화살표 유지) — Xvfb 에서 검증
- [ ] Fedora ISO 부팅 테스트: 자동 로그인, SELinux enforcing, firewalld 존, dnf-automatic, 메모리
- [ ] docklike 작업표시줄 기본값(고정 앱 목록 `docklike-2.rc` 의 pinned 경로 형식) 실제 ISO 에서 확인
- [ ] Anaconda 설치 흐름 (BIOS/UEFI, LUKS)
- [ ] RPM Fusion 코덱 설치 도우미, 릴리스 업그레이드 도우미
- [ ] 브라우저 v1: Vala/Rust 이식, EasyPrivacy 필터 자동 갱신, 비밀번호 관리자, WebRTC UI

## 0.2 – 다듬기

- 자체 앱 스토어 프론트엔드 검토 (GNOME Software 가 무겁다면 더 가벼운 대안)
- 장치 관리자 GUI, 시스템 정보 GUI (`kiyu-info` 의 GUI 판)
- 첫 로그인 환영 앱: 언어/입력기, 테마(밝게/어둡게), 게임/윈도우앱 설정을 한 화면에서
- 윈도우 11 스타일(가운데 정렬 패널) 옵션
- 노트북 전원 최적화 프로필 (tlp 또는 power-profiles-daemon)
- `trixie-backports` 커널 선택 설치 스크립트 (최신 하드웨어)
- 고급 보안 프로필 옵션: USBGuard, `ptrace_scope=2`, DNS over TLS

## 0.3 – Wayland

- XFCE Wayland 세션이 안정되면 기본 전환 (labwc 백엔드)
- 화면 공유/포털 재검증, fcitx5 Wayland 입력

## 이후

- ARM64 (라즈베리파이, Snapdragon 노트북) 이미지
- OEM 모드 (제조사 프리인스톨)
- 자체 미러/업데이트 채널 (Debian 위에 kiyu 전용 패키지 저장소)
