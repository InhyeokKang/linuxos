#!/usr/bin/python3
"""kiyu Imager — kiyu OS 를 USB/SD 카드에 굽는 전용 도구 (라즈베리파이 Imager 식).

흐름: [1] 이미지 고르기(로컬 .iso 또는 최신 kiyu 릴리스 내려받기) → [2] 대상 드라이브(이동식만) →
      [3] 굽기(확인 후 pkexec 로 파티션 해제 + dd + 선택적 검증, 진행률 표시).
쓰기 권한은 /usr/lib/kiyu-imager/kiyu-imager-write 를 pkexec 로 올려서 얻는다(디스크를 지우므로 매번 암호 확인).
"""
import json
import os
import subprocess
import sys
import threading
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

APP_ID = "org.kiyu.Imager"
WRITE_HELPER = "/usr/lib/kiyu-imager/kiyu-imager-write"
RELEASES_API = "https://api.github.com/repos/InhyeokKang/linuxos/releases/latest"
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "kiyu-imager")

CSS = b"""
.ki-title { font-size: 22px; font-weight: 700; }
.ki-step  { font-size: 13px; font-weight: 700; opacity: 0.6; letter-spacing: 1px; }
.ki-card  { background-color: @theme_base_color; border: 1px solid alpha(@theme_fg_color,0.12); border-radius: 16px; padding: 16px; }
.ki-pick  { font-size: 15px; }
.ki-warn  { color: #b23b00; }
.ki-big   { padding: 10px 22px; font-size: 15px; font-weight: 600; }
"""


def human(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


def root_disk():
    """루트(/) 가 올라간 물리 디스크 이름 (대상 목록에서 제외해 시스템 디스크를 지우지 않게)."""
    try:
        src = subprocess.run(["findmnt", "-n", "-o", "SOURCE", "/"], capture_output=True, text=True).stdout.strip()
        name = os.path.basename(src)
        out = subprocess.run(["lsblk", "-nso", "NAME", src], capture_output=True, text=True).stdout.split()
        return out[-1] if out else name
    except (OSError, IndexError):
        return ""


def list_targets():
    """이동식/USB/SD 디스크만. (name, path, model, size_bytes, size_str)"""
    try:
        data = json.loads(subprocess.run(
            ["lsblk", "-J", "-b", "-o", "NAME,SIZE,TYPE,RM,HOTPLUG,MODEL,TRAN,VENDOR"],
            capture_output=True, text=True, timeout=10).stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    rd = root_disk()
    out = []
    for d in data.get("blockdevices", []):
        if d.get("type") != "disk" or d.get("name") == rd:
            continue
        tran = (d.get("tran") or "")
        removable = d.get("rm") or d.get("hotplug") or tran in ("usb", "mmc") or (d.get("name") or "").startswith("mmcblk")
        if not removable:
            continue
        model = " ".join(x for x in (d.get("vendor"), d.get("model")) if x) or tran.upper() or "이동식 장치"
        out.append((d["name"], "/dev/" + d["name"], model.strip(), int(d["size"]), human(d["size"])))
    return out


class Imager(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="kiyu Imager")
        self.set_default_size(560, 560)
        self.set_icon_name("kiyu-imager")
        self.source_path = None
        self.writing = False

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin=24)
        self.add(outer)

        head = Gtk.Box(spacing=12)
        hi = Gtk.Image.new_from_icon_name("kiyu-imager", Gtk.IconSize.DIALOG)
        hi.set_pixel_size(44)
        head.pack_start(hi, False, False, 0)
        t = Gtk.Label(xalign=0)
        t.set_markup("<span>kiyu Imager</span>")
        t.get_style_context().add_class("ki-title")
        head.pack_start(t, True, True, 0)
        outer.pack_start(head, False, False, 0)

        # 1) 이미지
        outer.pack_start(self._step("1  이미지"), False, False, 0)
        c1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        c1.get_style_context().add_class("ki-card")
        self.src_label = Gtk.Label(label="이미지를 선택하세요", xalign=0)
        self.src_label.get_style_context().add_class("ki-pick")
        self.src_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        c1.pack_start(self.src_label, False, False, 0)
        row1 = Gtk.Box(spacing=8)
        b_file = Gtk.Button(label="파일 선택 (.iso)")
        b_file.connect("clicked", self._choose_file)
        b_dl = Gtk.Button(label="최신 kiyu 내려받기")
        b_dl.connect("clicked", self._download_latest)
        row1.pack_start(b_file, True, True, 0)
        row1.pack_start(b_dl, True, True, 0)
        c1.pack_start(row1, False, False, 0)
        self.dl_bar = Gtk.ProgressBar()
        self.dl_bar.set_no_show_all(True)
        self.dl_bar.set_show_text(True)
        c1.pack_start(self.dl_bar, False, False, 0)
        outer.pack_start(c1, False, False, 0)

        # 2) 대상
        outer.pack_start(self._step("2  대상 드라이브"), False, False, 0)
        c2 = Gtk.Box(spacing=8)
        c2.get_style_context().add_class("ki-card")
        self.target = Gtk.ComboBoxText()
        self.target.set_hexpand(True)
        c2.pack_start(self.target, True, True, 0)
        b_ref = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        b_ref.set_tooltip_text("드라이브 다시 검색")
        b_ref.connect("clicked", lambda *_: self.refresh_targets())
        c2.pack_start(b_ref, False, False, 0)
        outer.pack_start(c2, False, False, 0)

        # 3) 굽기
        outer.pack_start(self._step("3  굽기"), False, False, 0)
        self.verify = Gtk.CheckButton(label="굽고 나서 검증 (권장, 시간이 더 걸림)")
        self.verify.set_active(True)
        outer.pack_start(self.verify, False, False, 0)
        self.status = Gtk.Label(label="", xalign=0)
        self.status.set_line_wrap(True)
        outer.pack_start(self.status, False, False, 0)
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_no_show_all(True)
        outer.pack_start(self.progress, False, False, 0)
        self.write_btn = Gtk.Button(label="굽기")
        self.write_btn.get_style_context().add_class("ki-big")
        self.write_btn.get_style_context().add_class("suggested-action")
        self.write_btn.connect("clicked", self._start_write)
        outer.pack_start(self.write_btn, False, False, 0)

        warn = Gtk.Label(xalign=0)
        warn.set_markup("<small>대상 드라이브의 <b>모든 데이터가 지워집니다</b>. 시스템 디스크는 목록에 나오지 않습니다.</small>")
        warn.get_style_context().add_class("ki-warn")
        warn.set_line_wrap(True)
        outer.pack_start(warn, False, False, 0)

        self.show_all()
        self.refresh_targets()
        self._update_ready()

    def _step(self, text):
        lbl = Gtk.Label(label=text, xalign=0)
        lbl.get_style_context().add_class("ki-step")
        return lbl

    # ---------- 이미지 ----------
    def _set_source(self, path):
        self.source_path = path
        try:
            sz = human(os.path.getsize(path))
        except OSError:
            sz = "?"
        self.src_label.set_text(f"{os.path.basename(path)}  ({sz})")
        self._update_ready()

    def _choose_file(self, *_):
        d = Gtk.FileChooserDialog(title="kiyu 이미지 선택", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        d.add_buttons("취소", Gtk.ResponseType.CANCEL, "선택", Gtk.ResponseType.OK)
        f = Gtk.FileFilter()
        f.set_name("디스크 이미지 (*.iso, *.img)")
        f.add_pattern("*.iso")
        f.add_pattern("*.img")
        d.add_filter(f)
        if d.run() == Gtk.ResponseType.OK:
            self._set_source(d.get_filename())
        d.destroy()

    def _download_latest(self, *_):
        self.dl_bar.show()
        self.dl_bar.set_fraction(0)
        self.dl_bar.set_text("최신 릴리스 확인 중...")
        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        try:
            req = urllib.request.Request(RELEASES_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "kiyu-imager"})
            rel = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
            asset = next((a for a in rel.get("assets", []) if a["name"].endswith(".iso")), None)
            if not asset:
                return GLib.idle_add(self._dl_done, None, "릴리스에 ISO 파일이 없습니다. 파일 선택을 이용하세요.")
            os.makedirs(CACHE_DIR, exist_ok=True)
            dest = os.path.join(CACHE_DIR, asset["name"])
            url, total = asset["browser_download_url"], asset.get("size", 0)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "kiyu-imager"}), timeout=60) as r, open(dest, "wb") as out:
                done = 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if total:
                        GLib.idle_add(self._dl_progress, done / total, f"내려받는 중 {human(done)} / {human(total)}")
            GLib.idle_add(self._dl_done, dest, None)
        except Exception as e:  # noqa: BLE001 — 네트워크·JSON 등 무엇이든 사용자에게 표시
            GLib.idle_add(self._dl_done, None, f"내려받기 실패: {e}")

    def _dl_progress(self, frac, text):
        self.dl_bar.set_fraction(frac)
        self.dl_bar.set_text(text)
        return False

    def _dl_done(self, path, err):
        if err:
            self.dl_bar.set_text(err)
        else:
            self.dl_bar.hide()
            self._set_source(path)
        return False

    # ---------- 대상 ----------
    def refresh_targets(self):
        self.target.remove_all()
        self._targets = list_targets()
        for name, path, model, _b, sz in self._targets:
            self.target.append(path, f"{model} — {sz}  ({path})")
        if self._targets:
            self.target.set_active(0)
        else:
            self.target.append("", "이동식 드라이브 없음 (USB/SD 를 꽂고 다시 검색)")
            self.target.set_active(0)
        self._update_ready()

    def _selected_target(self):
        path = self.target.get_active_id()
        for t in getattr(self, "_targets", []):
            if t[1] == path:
                return t
        return None

    def _update_ready(self):
        ready = bool(self.source_path) and self._selected_target() is not None and not self.writing
        self.write_btn.set_sensitive(ready)

    # ---------- 굽기 ----------
    def _start_write(self, *_):
        tgt = self._selected_target()
        if not self.source_path or not tgt:
            return
        _name, path, model, _b, sz = tgt
        dlg = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text=f"{model} ({sz}) 에 굽습니다.")
        dlg.format_secondary_markup(f"<b>{path} 의 모든 데이터가 영구히 지워집니다.</b>\n계속할까요?")
        go = dlg.run() == Gtk.ResponseType.OK
        dlg.destroy()
        if not go:
            return
        self.writing = True
        self._update_ready()
        for w in (self.target,):
            w.set_sensitive(False)
        self.progress.show()
        self.progress.set_fraction(0)
        self.progress.set_text("준비 중")
        self.status.set_text("파티션 해제 후 굽는 중입니다. 창을 닫지 마세요.")
        cmd = ["pkexec", WRITE_HELPER, self.source_path, path, "verify" if self.verify.get_active() else "noverify"]
        threading.Thread(target=self._write_worker, args=(cmd,), daemon=True).start()

    def _write_worker(self, cmd):
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        except OSError as e:
            return GLib.idle_add(self._write_done, 1, f"실행 실패: {e}")
        for line in p.stdout:
            line = line.strip()
            if line.startswith("PROGRESS "):
                try:
                    _, phase, frac = line.split()
                    GLib.idle_add(self._write_progress, phase, float(frac))
                except ValueError:
                    pass
            elif line:
                GLib.idle_add(self.status.set_text, line)
        p.wait()
        GLib.idle_add(self._write_done, p.returncode, None)

    def _write_progress(self, phase, frac):
        self.progress.set_fraction(frac)
        self.progress.set_text(f"{'검증' if phase == 'verify' else '굽기'} {int(frac * 100)}%")
        return False

    def _write_done(self, rc, err):
        self.writing = False
        self.target.set_sensitive(True)
        self._update_ready()
        if rc == 0:
            self.progress.set_fraction(1.0)
            self.progress.set_text("완료")
            self.status.set_markup("<b>완료되었습니다.</b> 드라이브를 안전하게 뽑아 대상 컴퓨터에서 부팅하세요.")
        else:
            self.progress.set_text("실패")
            self.status.set_markup(f"<span foreground='#b23b00'>실패했습니다 (코드 {rc}). {err or ''}</span>")
        return False


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        (self.get_active_window() or Imager(self)).present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
