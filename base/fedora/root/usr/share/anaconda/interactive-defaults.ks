# kiyu 대화식 설치 기본값 (Anaconda interactive-defaults). 화면에서 바꿀 수 있다.
lang ko_KR.UTF-8
keyboard --xlayouts=kr
timezone Asia/Seoul --utc
# 디스크 암호화 기본 켬 (LUKS2). 설치 대상 화면에서 암호를 정하게 된다.
autopart --type=btrfs --encrypted --luks-version=luks2
firewall --enabled
selinux --enforcing
services --enabled=NetworkManager,chronyd,nftables
