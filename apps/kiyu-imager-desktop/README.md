# kiyu Imager (데스크톱)

kiyu ISO 를 USB·SD 카드에 굽는 **크로스 플랫폼**(Windows·macOS·Linux) 도구. 처음 kiyu 를 설치하려는 사람이
쓰던 컴퓨터(주로 Windows)에서 이 프로그램으로 USB 를 만들고, 그 USB 로 새 기기를 부팅해 kiyu 를 설치한다.
라즈베리파이 Imager 와 같은 역할.

- 기술: Electron + balena `etcher-sdk`(쓰기·검증) + `drivelist`(드라이브 감지) + `sudo-prompt`(관리자 권한).
  balenaEtcher 와 같은 라이브러리 스택이라 각 OS 의 저수준 쓰기·권한 처리가 검증돼 있다.
- 안전: 시스템 디스크는 목록에서 제외, 굽기 전 대상 모델·용량 확인, 쓰기 후 sha256 검증(기본 켬).
- 압축 이미지(.zip/.xz/.gz)도 자동 해제하며 굽는다.

## 개발
```sh
cd apps/kiyu-imager-desktop
npm install
npm start          # 개발 실행
npm run dist       # 현재 OS 용 설치본 (dist/)
```

## 배포 (CI)
`.github/workflows/build-imager.yml` 이 windows/macos/ubuntu 러너에서 각각 빌드해
Windows `.exe`(NSIS), macOS `.dmg`, Linux `.AppImage` 를 아티팩트로 올린다. 태그 푸시 시 릴리스에 첨부.

## 검증 상태
UI·빌드 스크립트는 작성됐고 CI 가 세 OS 설치본을 만든다. 실제 드라이브 쓰기·권한 승격은 각 OS 실기기에서
확인이 필요하다(이 개발 환경에서는 물리 드라이브가 없어 미검증).
