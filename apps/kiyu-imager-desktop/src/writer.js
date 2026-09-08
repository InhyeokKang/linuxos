// kiyu Imager 쓰기 도우미 — 관리자 권한(ELECTRON_RUN_AS_NODE=1)으로 실행. etcher-sdk 없이 순수 Node fs 로 굽고
// 검증한다(네이티브 모듈 의존 없음). 진행 상황은 progress 파일에 JSON 줄로 기록(GUI 가 폴링).
//   writer.js <image> <device> <verify|noverify> <progressFile>
const fs = require('fs');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const [imagePath, device, mode, progressFile] = process.argv.slice(2);
const verify = mode === 'verify';
const CHUNK = 4 * 1024 * 1024;

function emit(o) { try { fs.appendFileSync(progressFile, JSON.stringify(o) + '\n'); } catch (e) {} }
function sh(cmd, args) { try { return execFileSync(cmd, args, { stdio: ['ignore', 'pipe', 'ignore'] }).toString(); } catch (e) { return ''; } }

// 대상 장치의 마운트를 해제하고, 실제로 쓸 경로를 돌려준다 (macOS 는 raw 장치가 빠름).
function prepareTarget() {
  if (process.platform === 'linux') {
    try {
      const j = JSON.parse(sh('lsblk', ['-J', '-o', 'PATH,MOUNTPOINT', device]) || '{}');
      const walk = (nodes) => (nodes || []).forEach((n) => { if (n.mountpoint) sh('umount', [n.path]); walk(n.children); });
      walk(j.blockdevices);
    } catch (e) {}
    return device;
  }
  if (process.platform === 'darwin') {
    sh('diskutil', ['unmountDisk', 'force', device]);
    return device.replace('/dev/disk', '/dev/rdisk'); // raw = 훨씬 빠름
  }
  if (process.platform === 'win32') {
    // 물리 드라이브의 볼륨 문자를 떼어 파일시스템 잠금을 푼다(가능한 범위). device 예: \\.\PhysicalDrive2
    return device;
  }
  return device;
}

async function main() {
  emit({ type: 'status', text: '준비 중...' });
  const size = fs.statSync(imagePath).size;
  const target = prepareTarget();

  emit({ type: 'status', text: '굽는 중...' });
  await copy(imagePath, target, size, 'write');

  if (verify) {
    emit({ type: 'status', text: '검증 중...' });
    const a = await hashFile(imagePath, size, 'verify');
    const b = await hashDevice(target, size);
    if (a !== b) throw new Error('검증 실패: 이미지와 드라이브 내용이 다릅니다.');
  }
  emit({ type: 'done', ok: true });
}

function copy(src, dst, size, phase) {
  return new Promise((resolve, reject) => {
    let inFd, outFd;
    try { inFd = fs.openSync(src, 'r'); outFd = fs.openSync(dst, 'w'); }
    catch (e) { return reject(new Error('장치 열기 실패(권한/사용 중): ' + e.message)); }
    const buf = Buffer.allocUnsafe(CHUNK);
    let pos = 0, lastPct = -1;
    try {
      while (pos < size) {
        const n = fs.readSync(inFd, buf, 0, CHUNK, pos);
        if (n <= 0) break;
        fs.writeSync(outFd, buf, 0, n, pos);
        pos += n;
        const pct = Math.floor((pos / size) * 100);
        if (pct !== lastPct) { emit({ type: 'progress', phase, value: pos / size }); lastPct = pct; }
      }
      fs.fsyncSync(outFd);
    } catch (e) { try { fs.closeSync(inFd); } catch (x) {} try { fs.closeSync(outFd); } catch (x) {} return reject(e); }
    fs.closeSync(inFd); fs.closeSync(outFd); resolve();
  });
}

function hashFile(path, size, phase) {
  return new Promise((resolve, reject) => {
    let fd; try { fd = fs.openSync(path, 'r'); } catch (e) { return reject(e); }
    const h = crypto.createHash('sha256'); const buf = Buffer.allocUnsafe(CHUNK);
    let pos = 0, lastPct = -1;
    try {
      while (pos < size) {
        const n = fs.readSync(fd, buf, 0, Math.min(CHUNK, size - pos), pos);
        if (n <= 0) break;
        h.update(buf.subarray(0, n)); pos += n;
        const pct = Math.floor((pos / size) * 100);
        if (pct !== lastPct) { emit({ type: 'progress', phase, value: pos / size }); lastPct = pct; }
      }
    } catch (e) { fs.closeSync(fd); return reject(e); }
    fs.closeSync(fd); resolve(h.digest('hex'));
  });
}

function hashDevice(path, size) { return hashFile(path, size, 'verify'); }

main().catch((e) => { emit({ type: 'done', ok: false, error: e.message }); process.exit(1); });
