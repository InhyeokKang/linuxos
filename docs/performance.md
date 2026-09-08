# kiyu 성능 검토 — 크롬 사용 시 램/CPU/GPU·4K 재생

질문: **"kiyu 에서 크롬을 쓰면 윈도우보다 전체 램을 줄일 수 있나? CPU·GPU 부하는? 유튜브 4K 는 매끄럽나?"**

아래는 원리에 근거한 분석 + 실기기에서 직접 재보는 방법이다. (숫자는 하드웨어마다 다르므로
`kiyu-perf-check` 로 실측하는 것이 정확하다.)

## 1. 램 — 대체로 kiyu 가 낮다 (핵심은 OS 기본값)

브라우저 엔진(Chromium)은 OS 가 달라도 탭당 메모리가 비슷하다. 차이는 **OS 바탕 사용량**에서 난다.

| | 부팅 직후(브라우저 없이) 사용 램 |
|---|---|
| Windows 11 | 대략 3~4 GB (백그라운드 서비스·Defender·인덱싱·텔레메트리 포함) |
| **kiyu (XFCE)** | 대략 **0.5~0.8 GB** (XFCE 는 완성형 데스크톱 중 가장 가벼운 축) |

즉 같은 크롬 작업을 해도 **OS 가 먹는 몫이 2~3 GB 적어서, 시스템 전체 램 사용량은 kiyu 가 낮다.**
크롬 자체가 무거운 건 어느 OS나 같으니, 2 GB 기기에서 탭을 많이 열고 4K 를 틀면 여전히 빠듯하다 —
kiyu 의 이점은 "OS 여유가 2 GB+ 더 있다"는 것.
> 더 가볍게: 내장 **Taengja**(WebKitGTK) 브라우저는 크롬보다 프로세스·메모리가 적다. 저사양일수록 유리.

## 2. CPU — 유휴는 kiyu 가 낮고, 영상 부하는 "하드웨어 디코드" 여부가 전부

- **유휴**: 윈도우는 업데이트·인덱싱·텔레메트리로 백그라운드가 계속 움직인다. kiyu/XFCE 유휴 CPU 는 0~1%.
- **영상 재생**: 하드웨어 디코드가 되면 CPU 는 거의 안 오른다. 안 되면 CPU 소프트웨어 디코드로 여러 코어가 급등 → 4K 에서 프레임 드랍. → 3번이 관건.

## 3. GPU·4K 유튜브 — 원활하려면 "VA-API 하드웨어 디코드"가 켜져야 한다

4K 유튜브는 **VP9 또는 AV1** 코덱이다. 이걸 GPU 가 디코드해야(=VA-API) 매끄럽다.

- **리눅스 크롬/크로미엄은 VA-API 가 기본으로 꺼져 있다.** 그냥 설치해 쓰면 소프트웨어 디코드 →
  4K 에서 CPU 폭주·끊김. **`kiyu-setup-chrome` 가 이 플래그를 자동으로 켜 준다.**
- GPU 가 그 코덱을 디코드할 수 있어야 한다:
  - VP9 하드웨어 디코드: 인텔 Skylake(6세대)+·AMD·엔비디아 GTX 950+
  - AV1 하드웨어 디코드: 인텔 11세대+·AMD RDNA2+·엔비디아 RTX 30+
- **구형 저사양 기기(=kiyu 의 주 대상)**: iGPU 가 4K VP9/AV1 을 하드웨어로 못 풀면, OS 를 뭘 쓰든 4K 는
  버겁다. 이건 kiyu 의 한계가 아니라 GPU 한계다. 이 경우 **1080p 가 현실적인 스윗스팟**이고,
  `enhanced-h264ify` 확장으로 H.264 를 받으면 더 매끄럽다.

## 결론

- 램: **거의 확실히 kiyu 가 낮다** (OS 기본값 덕). 
- CPU: 유휴는 kiyu 가 낮고, 영상은 VA-API 만 켜지면 낮게 유지.
- 4K: **VA-API 켜기 + GPU 가 코덱 지원**이면 윈도우만큼 매끄럽다. 구형 GPU 면 4K 는 어느 OS나 한계 →
  1080p 권장. **가장 무난한 조합: `chromium-freeworld` + `kiyu-setup-codecs` + `kiyu-setup-chrome`.**

## 직접 측정하기 (실기기)

```sh
kiyu-setup-codecs      # VA-API 드라이버·코덱 설치
kiyu-setup-chrome      # chromium-freeworld + VA-API 플래그 (chrome 인자로 구글 크롬)
kiyu-perf-check        # 램/CPU/GPU/VA-API 지원 코덱 요약
# 유튜브 4K 재생 중 다른 터미널에서:
kiyu-perf-check --watch   # 램·CPU·GPU 실시간 (GPU 디코드면 CPU 낮게 유지)
```
브라우저에서 `chrome://gpu` → **Video Decode: Hardware accelerated** 이면 4K 부하가 GPU 로 간다.
