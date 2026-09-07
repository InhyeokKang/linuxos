.PHONY: all build clean check test test-uefi

all: build

## ISO 빌드 (root 필요)
build:
	sudo ./scripts/build.sh

## 빌드 산출물/캐시 정리
clean:
	sudo ./scripts/build.sh --clean

## 정적 검사 (빌드 불필요)
check:
	./scripts/check.sh

## QEMU 로 부팅 (BIOS)
test:
	./scripts/test-qemu.sh

## QEMU 로 부팅 (UEFI)
test-uefi:
	./scripts/test-qemu.sh --uefi
