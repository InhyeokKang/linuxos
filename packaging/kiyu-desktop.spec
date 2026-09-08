# kiyu-desktop: kiyu 의 데스크톱 구성(테마·패널·단축키), 자체 앱(탱자·빠른 설정·업데이트·Super 키), 브랜딩을
# 설치된 시스템에 업데이트로 배포하기 위한 패키지. 소스 tarball 은 scripts/build-rpm.sh 가 만든다.
%global debug_package %{nil}
Name:           kiyu-desktop
Version:        @VERSION@
Release:        @RELEASE@%{?dist}
Summary:        kiyu desktop configuration, apps and branding
License:        MIT
URL:            https://github.com/InhyeokKang/linuxos
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  gcc libX11-devel libXtst-devel python3
Requires:       xfce4-panel xfce4-whiskermenu-plugin xfce4-docklike-plugin xfwm4 xfdesktop picom
Requires:       python3-gobject webkit2gtk4.1 PackageKit PackageKit-glib librsvg2-tools brightnessctl libnotify
Requires:       fcitx5 fcitx5-hangul xdg-user-dirs

%description
Desktop defaults, own apps (Taengja browser, quick settings, updater, Super key helper) and branding for kiyu.
Installing or updating this package re-applies the kiyu look on a Fedora-based system.

%prep
%setup -q

%build
gcc -O2 %{?build_cflags} %{?build_ldflags} -o kiyu-superkey root/usr/src/kiyu/kiyu-superkey.c -lX11 -lXtst

%install
mkdir -p %{buildroot}
cp -a root/. %{buildroot}/
rm -f %{buildroot}/.buildstamp                       # 라이브 ISO 전용
install -D -m 0755 kiyu-superkey %{buildroot}%{_bindir}/kiyu-superkey
# 파일 목록 생성 (디렉터리는 다른 패키지 소유일 수 있어 파일만)
( cd %{buildroot} && find . \( -type f -o -type l \) | sed 's|^\./|/|' ) > files.list
# 설정 파일은 사용자가 고친 것을 보존
sed -i -e 's|^\(/etc/.*\)$|%%config(noreplace) \1|' files.list

%post
/usr/lib/kiyu/apply-system >/dev/null 2>&1 || :

%files -f files.list
