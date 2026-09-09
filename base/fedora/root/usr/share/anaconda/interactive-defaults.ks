# kiyu 대화식 설치 기본값 (Anaconda interactive-defaults). 화면에서 바꿀 수 있다.
lang ko_KR.UTF-8
keyboard --xlayouts=kr
timezone Asia/Seoul --utc
# 디스크 암호화 기본 켬 (LUKS2). 설치 대상 화면에서 암호를 정하게 된다.
autopart --type=btrfs --encrypted --luks-version=luks2
# kiyu 는 방화벽으로 nftables 를 쓰고 firewalld 를 넣지 않는다. Anaconda 는 firewall --enabled 일 때
# 대상 시스템의 /usr/bin/firewall-offline-cmd 가 없으면 FirewallConfigurationError 를 던져 설치가
# 크래시한다(결점 보고 창). --use-system-defaults 는 방화벽 설정을 건너뛰어 kiyu 의 nftables 설정을 그대로 둔다.
firewall --use-system-defaults
selinux --enforcing
services --enabled=NetworkManager,chronyd,nftables
