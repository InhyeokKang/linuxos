#!/bin/bash
# kiwi 가 패키지 설치와 root/ 오버레이 복사 후 이미지 chroot 안에서 실행하는 스크립트.
# (Debian 트리의 hooks/normal/* 에 해당)
set -euxo pipefail
OS_ID=kiyu

# ---- 정체성 -----------------------------------------------------------------
if [ -f "/usr/lib/${OS_ID}/os-release" ]; then
    rm -f /etc/os-release
    cp "/usr/lib/${OS_ID}/os-release" /usr/lib/os-release
    ln -s ../usr/lib/os-release /etc/os-release
fi
[ -f "/usr/lib/${OS_ID}/issue" ] && cp "/usr/lib/${OS_ID}/issue" /etc/issue

# ---- 라이브 세션 (livesys-scripts) ---------------------------------------------
cat > /etc/sysconfig/livesys <<'LIVESYS'
livesys_session="xfce"
LIVESYS

# ---- 디스플레이 매니저 / 세션 ----------------------------------------------------
systemctl set-default graphical.target
systemctl enable lightdm.service 2>/dev/null || echo "WARN: cannot enable lightdm"
echo "/usr/sbin/lightdm" > /etc/X11/default-display-manager 2>/dev/null || true

# ---- 보안 / 서비스 -----------------------------------------------------------
en() { systemctl enable "$1" 2>/dev/null || echo "WARN: cannot enable $1"; }
en nftables.service
systemctl disable firewalld.service 2>/dev/null || true
en dnf5-automatic.timer || en dnf-automatic.timer
en fstrim.timer
en NetworkManager.service
en chronyd.service
en kiyu-firstboot.service
en livesys.service; en livesys-late.service
systemctl disable ModemManager.service 2>/dev/null || true
# Ctrl+Alt+Del 로 콘솔에서 재부팅되지 않게 (Fedora 는 /etc 에 링크가 이미 있어 mask 대신 직접 /dev/null 로)
rm -f /etc/systemd/system/ctrl-alt-del.target
ln -s /dev/null /etc/systemd/system/ctrl-alt-del.target
# 방화벽 규칙 문법 검사 (빌드 단계에서 오류를 잡음)
nft -c -f /etc/nftables/kiyu.nft
passwd -l root >/dev/null 2>&1 || true
sed -i 's/^\(HOME_MODE\s\+\).*/\10700/' /etc/login.defs 2>/dev/null || true

# ---- 브랜딩 이미지·배경·패널 기본값·플러그인 in-process 등: /usr/lib/kiyu/apply-system (RPM %post 와 공용) ----
# 탱자 광고·추적 차단 목록: EasyList / EasyPrivacy / List-KR 을 받아 WebKit 규칙으로 변환 (실패해도 빌드는 계속,
# 그때는 브라우저 내장 소형 목록만 쓴다). 결과: /usr/share/taengja/filters/*.json
mkdir -p /usr/share/taengja/filters
fl=/tmp/filters; mkdir -p "$fl"
fetch() { curl -fsSL --max-time 60 --retry 2 -o "$2" "$1" 2>/dev/null && [ -s "$2" ]; }
fetch https://easylist.to/easylist/easyprivacy.txt "$fl/easyprivacy.txt" || echo "경고: easyprivacy 다운로드 실패"
fetch https://easylist.to/easylist/easylist.txt "$fl/easylist.txt" || echo "경고: easylist 다운로드 실패"
fetch https://raw.githubusercontent.com/List-KR/List-KR/master/filter.txt "$fl/listkr.txt" || echo "경고: List-KR 다운로드 실패"
if [ -x /usr/lib/taengja/abp2webkit.py ]; then
    # 추적 차단(EasyPrivacy) 은 통째로, 광고(EasyList) 는 네트워크 규칙 위주, 한국 사이트(List-KR) 는 통째로
    [ -s "$fl/easyprivacy.txt" ] && python3 /usr/lib/taengja/abp2webkit.py --max 30000 --no-cosmetic -o /usr/share/taengja/filters/10-easyprivacy.json "$fl/easyprivacy.txt"
    [ -s "$fl/easylist.txt" ] && python3 /usr/lib/taengja/abp2webkit.py --max 30000 --no-cosmetic -o /usr/share/taengja/filters/20-easylist.json "$fl/easylist.txt"
    [ -s "$fl/listkr.txt" ] && python3 /usr/lib/taengja/abp2webkit.py --max 15000 -o /usr/share/taengja/filters/30-listkr.json "$fl/listkr.txt"
    ls -la /usr/share/taengja/filters/
fi
rm -rf "$fl"
# ---- kiyu-superkey 컴파일 (Super 탭 → 시작 메뉴; 소스는 apps/kiyu-superkey) ----------
if [ -f /usr/src/kiyu/kiyu-superkey.c ] && command -v gcc >/dev/null 2>&1; then
    gcc -O2 -o /usr/bin/kiyu-superkey /usr/src/kiyu/kiyu-superkey.c -lX11 -lXtst
    chmod 0755 /usr/bin/kiyu-superkey
    echo "kiyu-superkey built"
fi

# ---- kiyu 업데이트 저장소: 서명 공개키가 올라와 있으면 켠다 (없으면 enabled=0 그대로) ----
if curl -fsSL --max-time 20 -o /tmp/RPM-GPG-KEY-kiyu https://raw.githubusercontent.com/InhyeokKang/linuxos/kiyu-repo/RPM-GPG-KEY-kiyu 2>/dev/null \
   && grep -q "BEGIN PGP PUBLIC KEY" /tmp/RPM-GPG-KEY-kiyu; then
    install -D -m 0644 /tmp/RPM-GPG-KEY-kiyu /etc/pki/rpm-gpg/RPM-GPG-KEY-kiyu
    rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-kiyu || true
    sed -i 's|^enabled=0|enabled=1|; s|^gpgkey=.*|gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-kiyu|' /etc/yum.repos.d/kiyu.repo
    echo "kiyu repo: enabled (signed)"
else
    echo "kiyu repo: 서명 키 없음, 저장소는 비활성 상태로 둠"
fi
rm -f /tmp/RPM-GPG-KEY-kiyu

# ---- 파일 반영 (이미지 변환, 배경 교체, 패널 기본값, 캐시) ----
chmod 0755 /usr/lib/${OS_ID}/apply-system
/usr/lib/${OS_ID}/apply-system

# ---- SELinux 라벨 -------------------------------------------------------------
if [ -x /usr/sbin/setfiles ] && [ -f /etc/selinux/targeted/contexts/files/file_contexts ]; then
    setfiles -F -e /proc -e /sys -e /dev -e /run /etc/selinux/targeted/contexts/files/file_contexts / || true
fi

# ---- 글꼴: IBM Plex Sans KR / Inter (있으면), Pretendard (GitHub 릴리스, 실패해도 빌드는 계속) --------
dnf -y install --setopt=install_weak_deps=False ibm-plex-sans-kr-fonts rsms-inter-fonts 2>/dev/null \
    || dnf -y install --setopt=install_weak_deps=False ibm-plex-sans-kr-fonts 2>/dev/null || echo "WARN: optional fonts not installed"
PRET_VER=1.3.9
if curl -fsSL --retry 2 -o /tmp/pretendard.zip "https://github.com/orioncactus/pretendard/releases/download/v${PRET_VER}/Pretendard-${PRET_VER}.zip"; then
    mkdir -p /usr/share/fonts/pretendard
    unzip -qo -j /tmp/pretendard.zip '*/variable/PretendardVariable.ttf' -d /usr/share/fonts/pretendard/ \
        || unzip -qo -j /tmp/pretendard.zip '*PretendardVariable.ttf' -d /usr/share/fonts/pretendard/ || true
    rm -f /tmp/pretendard.zip
    ls /usr/share/fonts/pretendard/ || true
else
    echo "WARN: Pretendard download failed; falling back to Plex/Source Han"
fi
fc-cache -f || true

# ---- ld.so 캐시 (없으면 첫 부팅에 ldconfig.service 가 16초 걸림) ----------------------
ldconfig || true

# ---- 정리 ----------------------------------------------------------------------
dnf5 clean all 2>/dev/null || dnf clean all 2>/dev/null || true
rm -rf /var/cache/dnf /var/cache/libdnf5 /tmp/* /var/tmp/*
rm -f /etc/machine-id; touch /etc/machine-id
exit 0
