#!/usr/bin/env bash
# CI 용: Fedora 컨테이너 안에서 kiyu-desktop RPM 을 빌드하고 dnf 저장소 디렉터리(repo/)를 만든다.
# 환경 변수 KIYU_RPM_GPG_KEY(ASCII armored 비밀키), KIYU_RPM_GPG_PASS 가 있으면 RPM 과 repomd.xml 을 서명한다.
set -euo pipefail
cd "$(dirname "$0")/.."
dnf -y install --setopt=install_weak_deps=False rpm-build rpm-sign createrepo_c gcc libX11-devel libXtst-devel python3 curl git gnupg2 >/dev/null
git config --global --add safe.directory "$PWD"
scripts/build-rpm.sh
rm -rf repo; mkdir -p repo/x86_64; cp out/rpm/*.rpm repo/x86_64/
if [ -n "${KIYU_RPM_GPG_KEY:-}" ]; then
    echo "$KIYU_RPM_GPG_KEY" | gpg --batch --import
    KEYID=$(gpg --list-secret-keys --with-colons | awk -F: '/^sec/{print $5; exit}')
    {
        echo '%_signature gpg'
        echo "%_gpg_name $KEYID"
        echo "%__gpg_sign_cmd %{__gpg} gpg --batch --pinentry-mode loopback --passphrase '${KIYU_RPM_GPG_PASS:-}' --no-armor --no-secmem-warning -u '%{_gpg_name}' -sbo %{__signature_filename} %{__plaintext_filename}"
    } > ~/.rpmmacros
    rpm --addsign repo/x86_64/*.rpm
    gpg --armor --export "$KEYID" > repo/RPM-GPG-KEY-kiyu
    createrepo_c repo
    gpg --batch --pinentry-mode loopback --passphrase "${KIYU_RPM_GPG_PASS:-}" --detach-sign --armor repo/repodata/repomd.xml
    echo "signed with $KEYID"
else
    createrepo_c repo
    echo "unsigned repo (KIYU_RPM_GPG_KEY 시크릿 없음)"
fi
find repo -type f | sort | head -40
