# kiyu Imager

kiyu 를 USB 메모리·SD 카드에 굽는 전용 도구 (라즈베리파이 Imager 식). kiyu 안에 기본 포함되며 시작 메뉴 > 시스템 에 있다.

## 흐름
1. **이미지**: 로컬 `.iso`/`.img` 를 고르거나 "최신 kiyu 내려받기"(GitHub 릴리스 API 로 최신 ISO 다운로드).
2. **대상 드라이브**: 이동식(USB/SD)만 자동 감지해 목록에 올린다. 시스템 디스크(루트가 올라간 디스크)는 목록에서 제외해 실수로 지우는 것을 막는다.
3. **굽기**: 확인 대화상자에서 대상 모델·용량을 보이고 진행. `kiyu-imager-write` 가 pkexec 로 권한을 얻어 파티션 해제 → `dd` 쓰기 → (선택) sha256 검증까지 하고 진행률을 GUI 에 돌려준다.

## 구성
- GUI: `apps/kiyu-imager/kiyu-imager.py` (GTK3), 래퍼 `kiyu-imager`.
- 쓰기 도우미(root): `apps/kiyu-imager/kiyu-imager-write` — 시스템 디스크면 거부, `dd bs=4M conv=fsync oflag=direct`, 검증은 이미지 크기만큼 읽어 해시 비교.
- 권한: `org.kiyu.imager.policy` (pkexec, 디스크를 지우므로 매번 관리자 인증).
- 의존: util-linux(lsblk/wipefs), coreutils(dd/sha256sum), udisks2(unmount), polkit — 모두 kiyu 에 이미 포함.

## 한계
- 현재는 kiyu(리눅스)에서 도는 GTK 앱이다. 처음 kiyu 를 설치하려는 **윈도우 사용자용 Windows 판은 별도 과제**(크로스 플랫폼 빌드·서명 필요). 그 전까지 윈도우에서는 balenaEtcher/Rufus 로 kiyu ISO 를 구우면 된다.
- QEMU/CI 에는 이동식 드라이브가 없어 UI 만 검증했고, 실제 쓰기·검증은 실기기 확인 대상이다.
