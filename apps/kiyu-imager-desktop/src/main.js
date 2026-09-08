// kiyu Imager (데스크톱, 크로스 플랫폼). 윈도우·맥·리눅스에서 kiyu ISO 를 USB/SD 에 굽는다.
// GUI 는 권한 없이 뜨고, 실제 쓰기는 sudo-prompt 로 관리자 권한을 받아 writer.js 를 별도 프로세스로 돌린다
// (balenaEtcher 와 같은 "권한 승격된 writer" 구조). 쓰기·검증은 balena etcher-sdk 가 담당.
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const https = require('https');
const drivelist = require('drivelist');
const sudo = require('sudo-prompt');

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 640, height: 680, resizable: false,
    title: 'kiyu Imager',
    icon: path.join(__dirname, '..', 'build', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false },
  });
  win.setMenuBarVisibility(false);
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());

// 이동식 드라이브만 (시스템 디스크 제외)
ipcMain.handle('list-drives', async () => {
  const drives = await drivelist.list();
  return drives
    .filter((d) => !d.isSystem && !d.isVirtual && (d.isRemovable || d.isCard || d.isUSB) && d.size)
    .map((d) => ({
      device: d.device, raw: d.raw, description: d.description || d.busType || '이동식 장치',
      size: d.size, mountpoints: (d.mountpoints || []).map((m) => m.path),
    }));
});

// 로컬 이미지 파일 선택
ipcMain.handle('choose-file', async () => {
  const r = await dialog.showOpenDialog(win, {
    title: 'kiyu 이미지 선택',
    filters: [{ name: '디스크 이미지', extensions: ['iso', 'img', 'zip', 'xz', 'gz', 'bz2'] }],
    properties: ['openFile'],
  });
  if (r.canceled || !r.filePaths[0]) return null;
  const p = r.filePaths[0];
  return { path: p, size: fs.statSync(p).size, name: path.basename(p) };
});

// 최신 kiyu 릴리스 ISO 를 내려받는다 (진행률은 renderer 로)
ipcMain.handle('download-latest', async (evt) => {
  const rel = await getJSON('https://api.github.com/repos/InhyeokKang/linuxos/releases/latest');
  const asset = (rel.assets || []).find((a) => a.name.endsWith('.iso'));
  if (!asset) throw new Error('릴리스에 ISO 파일이 없습니다. 파일 선택을 이용하세요.');
  const dest = path.join(os.tmpdir(), asset.name);
  await download(asset.browser_download_url, dest, asset.size, (frac, text) => evt.sender.send('dl-progress', frac, text));
  return { path: dest, size: fs.statSync(dest).size, name: asset.name };
});

// 굽기: writer.js 를 관리자 권한으로 실행하고 진행률 파일을 폴링
ipcMain.handle('flash', async (evt, imagePath, drive, verify) => {
  const progressFile = path.join(os.tmpdir(), `kiyu-imager-${Date.now()}.progress`);
  fs.writeFileSync(progressFile, '');
  const isDev = !app.isPackaged;
  const nodeBin = isDev ? process.execPath : process.execPath; // 배포 시 electron 바이너리를 node 모드로
  const writer = path.join(__dirname, 'writer.js');
  const target = process.platform === 'win32' ? (drive.raw || drive.device) : drive.device;
  const args = [writer, imagePath, target, verify ? 'verify' : 'noverify', progressFile];
  const quoted = [nodeBin, ...args].map((a) => `"${a}"`).join(' ');

  let done = false, result = null;
  const poll = setInterval(() => {
    let txt = '';
    try { txt = fs.readFileSync(progressFile, 'utf8'); } catch (e) { return; }
    const lines = txt.trim().split('\n').filter(Boolean);
    const last = lines[lines.length - 1];
    if (!last) return;
    try {
      const o = JSON.parse(last);
      if (o.type === 'progress') evt.sender.send('flash-progress', o.phase, o.value);
      else if (o.type === 'status') evt.sender.send('flash-status', o.text);
      else if (o.type === 'done') { result = o; }
    } catch (e) { /* 부분 기록 무시 */ }
  }, 400);

  return await new Promise((resolve) => {
    sudo.exec(quoted, { name: 'kiyu Imager', env: { ELECTRON_RUN_AS_NODE: '1' } }, (err, stdout, stderr) => {
      done = true;
      clearInterval(poll);
      try { fs.unlinkSync(progressFile); } catch (e) {}
      if (result && result.ok) return resolve({ ok: true });
      resolve({ ok: false, error: (result && result.error) || (err && err.message) || (stderr || '').toString() || '알 수 없는 오류' });
    });
  });
});

function getJSON(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'kiyu-imager', Accept: 'application/vnd.github+json' } }, (res) => {
      if (res.statusCode >= 300 && res.headers.location) return resolve(getJSON(res.headers.location));
      let s = '';
      res.on('data', (d) => (s += d));
      res.on('end', () => { try { resolve(JSON.parse(s)); } catch (e) { reject(e); } });
    }).on('error', reject);
  });
}

function download(url, dest, total, onProgress) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'kiyu-imager' } }, (res) => {
      if (res.statusCode >= 300 && res.headers.location) return resolve(download(res.headers.location, dest, total, onProgress));
      if (res.statusCode !== 200) return reject(new Error('HTTP ' + res.statusCode));
      const out = fs.createWriteStream(dest);
      let done = 0;
      res.on('data', (d) => { done += d.length; if (total) onProgress(done / total, `내려받는 중 ${human(done)} / ${human(total)}`); });
      res.pipe(out);
      out.on('finish', () => out.close(() => resolve()));
      out.on('error', reject);
    }).on('error', reject);
  });
}

function human(n) {
  const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${i === 0 ? n : n.toFixed(1)} ${u[i]}`;
}
