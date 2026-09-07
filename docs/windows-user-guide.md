# 윈도우 사용자를 위한 대응표

## 단축키

| 윈도우 | Haneul OS | 동작 |
|---|---|---|
| `Win` | `Win` (혼자 눌렀다 뗌) | 시작 메뉴. `Alt+F1` 도 동일 |
| `Win+E` | `Win+E` | 파일 탐색기 (Thunar) |
| `Win+D` | `Win+D` | 바탕화면 보기 |
| `Win+L` | `Win+L` | 화면 잠금 |
| `Win+R` | `Win+R` | 실행 |
| `Win+I` | `Win+I` | 설정 |
| `Win+S` | `Win+S` | 앱 검색 |
| `Win+V` | `Win+V` | 클립보드 기록 |
| `Win+P` | `Win+P` | 디스플레이 전환 |
| `Win+A` | `Win+A` | 소리 설정 |
| `Win+↑ ↓ ← →` | 동일 | 창 최대화 / 최소화 / 왼쪽·오른쪽 반 |
| `Alt+Tab` | `Alt+Tab` | 창 전환 |
| `Alt+F4` | `Alt+F4` | 창 닫기 |
| `Ctrl+Shift+Esc`, `Ctrl+Alt+Del` | 동일 | 작업 관리자 |
| `PrtSc` | `PrtSc` | 전체 화면 캡처 → 클립보드 |
| `Win+Shift+S` | `Win+Shift+S` | 영역 캡처 → 클립보드 |
| `Alt+PrtSc` | `Alt+PrtSc` | 현재 창 캡처 |
| (없음) | `Ctrl+Alt+T` | 터미널 |
| `한/영` | `한/영` 또는 `Shift+Space` | 한글/영문 전환 (fcitx5) |

## 프로그램

| 윈도우 | Haneul OS | 비고 |
|---|---|---|
| 파일 탐색기 | Thunar | 경로 표시줄, 주소 직접 입력, 휴지통, 외장 드라이브 자동 마운트, 윈도우 NTFS 파티션 읽기/쓰기 |
| Edge | Firefox | PDF 도 열림 |
| 메모장 | Mousepad | |
| 사진 | Ristretto | |
| 미디어 플레이어 | mpv | 거의 모든 코덱 내장 |
| 계산기 | Galculator | |
| 압축 | Xarchiver | zip / 7z / rar / tar |
| Word / Excel / PowerPoint | LibreOffice Writer / Calc / Impress | docx/xlsx/pptx 열고 저장 가능 |
| 작업 관리자 | 작업 관리자 (xfce4-taskmanager) | |
| 설정 | 설정 관리자 | |
| Microsoft Store | 소프트웨어 (GNOME Software) | Flathub 앱 + Debian 패키지 |
| 디스크 관리 | GParted | |
| 장치 관리자 | (터미널) `lspci`, `lsusb` | GUI 는 로드맵 |
| 제어판 > 프린터 | 프린터 설정 (system-config-printer) | |
| 블루투스 | Blueman | |
| 윈도우 업데이트 | 자동 (보안), 나머지는 소프트웨어 앱에서 | |
| Steam | Steam | 시작 메뉴 > Haneul 게임 설정 |
| .exe 실행 | Wine / Bottles | 시작 메뉴 > Haneul 윈도우 프로그램 설정 |

## 처음 만나는 개념

- **관리자 비밀번호 창** = UAC. 프로그램 설치, 설정 변경 때 뜹니다. 본인 계정 비밀번호를 입력하세요.
- **C: 드라이브가 없다.** 모든 것이 `/` 아래 하나의 트리입니다. 내 문서는 `홈` 폴더. 외장 드라이브는 왼쪽 사이드바에 자동으로 나타납니다.
- **프로그램 설치는 스토어에서.** 웹에서 설치 파일을 받아 실행하는 방식은 예외적입니다. `.deb` 파일은 더블클릭하면 됩니다.
- **백신이 없다.** 앱은 스토어(서명 검증), 샌드박스, 방화벽, 자동 업데이트로 보호됩니다. `haneul-info` 로 상태 확인.
- **재부팅이 드물다.** 업데이트 후에도 대부분 재부팅이 필요 없습니다. 커널 업데이트 때만 알림이 뜹니다.

## 게임

1. 시작 메뉴 > **Haneul 게임 설정** 실행 (Steam, Proton-GE, GameMode, MangoHud 설치. NVIDIA 면 드라이버 선택).
2. Steam > 설정 > 호환 > "모든 타이틀에 Steam Play 사용" 켜기.
3. 호환성은 [ProtonDB](https://www.protondb.com) 에서 확인. 대부분의 싱글/협동 게임은 그대로 동작합니다. 커널 수준 안티치트(발로란트, 배틀그라운드 일부 등)는 동작하지 않습니다.

## 윈도우 프로그램 (.exe)

1. 시작 메뉴 > **Haneul 윈도우 프로그램 설정** 실행.
2. `.exe` 더블클릭 → Wine 으로 실행. 잘 안 되면 **Bottles** 에서 프로그램별 환경을 만들어 설치.
3. 카카오톡, 반디집, 알집 같은 국내 앱 대부분은 Wine 으로 동작합니다. 은행/공인인증 관련 보안 프로그램은 동작하지 않습니다 (브라우저 기반 인증서 사용 권장).
