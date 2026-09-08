// kiyu Imager 쓰기 도우미 — 관리자 권한으로 실행됨(ELECTRON_RUN_AS_NODE=1). etcher-sdk 로 굽고 검증한다.
// 진행 상황은 인자로 받은 progress 파일에 JSON 줄로 기록한다(GUI 가 폴링).
//   writer.js <image> <rawdevice> <verify|noverify> <progressFile>
const fs = require('fs');
const { sourceDestination, multiWrite } = require('etcher-sdk');

const [imagePath, rawDevice, mode, progressFile] = process.argv.slice(2);
const verify = mode === 'verify';

function emit(obj) {
  try { fs.appendFileSync(progressFile, JSON.stringify(obj) + '\n'); } catch (e) {}
}

async function main() {
  emit({ type: 'status', text: '준비 중...' });
  const source = new sourceDestination.File({ path: imagePath });
  const innerSource = await source.getInnerSource(); // .iso 는 그대로, .zip/.xz 등은 자동 해제
  const destination = new sourceDestination.BlockDevice({
    drive: { device: rawDevice, raw: rawDevice, size: null, isSystem: false },
    unmountOnSuccess: true,
    write: true,
    direct: true,
  });
  await destination.open();
  try {
    await multiWrite.pipeSourceToDestinations({
      source: innerSource,
      destinations: [destination],
      verify,
      onFail: (_dest, error) => emit({ type: 'status', text: '오류: ' + error.message }),
      onProgress: (p) => {
        // p.type: 'flashing' | 'verifying'
        const value = p.percentage != null ? p.percentage / 100 : (p.position && p.size ? p.position / p.size : 0);
        emit({ type: 'progress', phase: p.type === 'verifying' ? 'verify' : 'write', value });
      },
    });
    emit({ type: 'done', ok: true });
  } finally {
    await destination.close().catch(() => {});
  }
}

main().catch((e) => { emit({ type: 'done', ok: false, error: e.message }); process.exit(1); });
