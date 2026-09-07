# 로드맵

## 0.1 – 스캐폴드 (현재)

설정 트리, 정적 검사, 문서 완료. **아직 실제 빌드/부팅 검증 전.** 첫 빌드에서 확인할 것:

- [ ] 모든 패키지 이름이 trixie 에 존재하는지 (`E: Unable to locate package`)
- [ ] live-build 버전이 `includes.chroot_before_packages` 를 지원하는지 (bookworm 1:20230502 이상)
- [ ] `--uefi-secure-boot auto` 로 Secure Boot 켠 VM 에서 부팅
- [ ] 라이브 자동 로그인, 패널 배치, 단축키, 한글 입력
- [ ] xfdesktop 이 `monitor0` 기본 배경을 실제 모니터 이름으로 이관하는지 (아니면 훅에서 모니터별 설정 필요)
- [ ] 패널 launcher 플러그인이 절대 경로 `.desktop` 항목을 받아들이는지
- [ ] `mate-polkit` 에이전트 경로 (`/usr/lib/haneul/polkit-agent` 후보 목록)
- [ ] Calamares: 모듈 이름/설정 키가 trixie 의 3.3.x 와 맞는지, BIOS/UEFI 설치, LUKS 설치, 윈도우 듀얼부팅 감지
- [ ] 설치 후 `live` 사용자 제거, 설치 아이콘 제거, `haneul-firstboot` 재실행
- [ ] 유휴 RAM 측정 → README 수치 갱신

## 0.2 – 다듬기

- 자체 앱 스토어 프론트엔드 검토 (GNOME Software 가 무겁다면 더 가벼운 대안)
- 장치 관리자 GUI, 시스템 정보 GUI (`haneul-info` 의 GUI 판)
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
- 자체 미러/업데이트 채널 (Debian 위에 Haneul 전용 패키지 저장소)
