const $ = (id) => document.getElementById(id);
let source = null, drives = [], busy = false;

function human(n){const u=['B','KB','MB','GB','TB'];let i=0;while(n>=1024&&i<u.length-1){n/=1024;i++;}return (i?n.toFixed(1):n)+' '+u[i];}
function ready(){ $('btn-flash').disabled = !(source && drives.length && $('drive').value && !busy); }

$('btn-file').onclick = async () => { const s = await window.kiyu.chooseFile(); if (s){ source=s; $('src-label').textContent = `${s.name} (${human(s.size)})`; ready(); } };
$('btn-dl').onclick = async () => {
  $('dl-bar').hidden=false; $('dl-text').textContent='최신 릴리스 확인 중...';
  try { const s = await window.kiyu.downloadLatest(); source=s; $('dl-bar').hidden=true; $('src-label').textContent=`${s.name} (${human(s.size)})`; ready(); }
  catch(e){ $('dl-text').textContent = '내려받기 실패: '+e.message; }
};
window.kiyu.onDlProgress((frac,text)=>{ $('dl-bar').value=frac; $('dl-text').textContent=text; });

async function refresh(){
  drives = await window.kiyu.listDrives();
  const sel = $('drive'); sel.innerHTML='';
  if (!drives.length){ const o=document.createElement('option'); o.value=''; o.textContent='이동식 드라이브 없음 (USB/SD 를 꽂고 다시 검색)'; sel.appendChild(o); }
  drives.forEach((d,i)=>{ const o=document.createElement('option'); o.value=String(i); o.textContent=`${d.description} — ${human(d.size)} (${d.device})`; sel.appendChild(o); });
  ready();
}
$('btn-refresh').onclick = refresh;
$('drive').onchange = ready;

$('btn-flash').onclick = async () => {
  const d = drives[Number($('drive').value)]; if (!source || !d) return;
  if (!confirm(`${d.description} (${human(d.size)}) 에 굽습니다.\n${d.device} 의 모든 데이터가 영구히 지워집니다. 계속할까요?`)) return;
  busy=true; ready();
  $('flash-bar').hidden=false; $('flash-bar').value=0; $('status').textContent='관리자 권한을 확인하고 굽는 중입니다...';
  const r = await window.kiyu.flash(source.path, d, $('verify').checked);
  busy=false; ready();
  if (r.ok){ $('flash-bar').value=1; $('status').innerHTML='<b>완료되었습니다.</b> 드라이브를 뽑아 새 기기에서 부팅하세요.'; }
  else { $('status').innerHTML = `<span style="color:#b23b00">실패: ${r.error||''}</span>`; }
};
window.kiyu.onFlashProgress((phase,value)=>{ $('flash-bar').value=value; $('status').textContent=(phase==='verify'?'검증':'굽기')+` ${Math.round(value*100)}%`; });
window.kiyu.onFlashStatus((t)=>{ $('status').textContent=t; });

refresh();
