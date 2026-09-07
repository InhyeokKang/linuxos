#!/usr/bin/python3
"""kiyu 업데이트 (Windows 업데이트처럼).

설정 > 업데이트 로 들어오면 자동으로 확인하고, [다운로드 및 설치] 한 번으로 시스템 패키지(PackageKit)와
Flatpak 앱을 함께 갱신한다. 진행률 표시, 끝나면 다시 시작 필요 여부 안내.
권한: /usr/share/polkit-1/rules.d/50-kiyu-update.rules 가 로그인한 wheel 사용자에게 암호 없이 허용.
"""
import datetime
import os
import shutil
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("PackageKitGlib", "1.0")
from gi.repository import GLib, Gtk, PackageKitGlib as PK  # noqa: E402

APP_ID = "org.kiyu.Update"
STATE_DIR = os.path.join(GLib.get_user_config_dir(), "kiyu")
REBOOT_PKGS = ("kernel", "kernel-core", "systemd", "glibc", "dbus", "mesa-dri-drivers", "xorg-x11-server-Xorg", "linux-firmware")

CSS = b"""
.ku-title { font-size: 20px; font-weight: 700; }
.ku-status { font-size: 15px; font-weight: 600; }
.ku-muted { opacity: 0.7; }
.ku-card { background-color: @theme_base_color; border: 1px solid alpha(@theme_fg_color, 0.12); border-radius: 14px; padding: 18px; }
.ku-big { padding: 8px 18px; }
"""


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class UpdateWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="업데이트")
        self.set_default_size(640, 520)
        self.set_icon_name("kiyu-update")
        self.client = PK.Client()
        self.client.set_interactive(True)
        self.updates = []
        self.busy = False
        self.needs_reboot = False

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin=24)
        self.add(outer)

        head = Gtk.Box(spacing=12)
        hi = Gtk.Image.new_from_icon_name("kiyu-update", Gtk.IconSize.DIALOG)
        hi.set_pixel_size(48)
        head.pack_start(hi, False, False, 0)
        t = Gtk.Label(label="업데이트", xalign=0)
        t.get_style_context().add_class("ku-title")
        head.pack_start(t, True, True, 0)
        outer.pack_start(head, False, False, 0)

        # 상태 카드
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.get_style_context().add_class("ku-card")
        row = Gtk.Box(spacing=12)
        self.icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic", Gtk.IconSize.DND)
        row.pack_start(self.icon, False, False, 0)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.status = Gtk.Label(label="확인 중...", xalign=0)
        self.status.get_style_context().add_class("ku-status")
        self.detail = Gtk.Label(label="", xalign=0)
        self.detail.get_style_context().add_class("ku-muted")
        self.detail.set_line_wrap(True)
        vb.pack_start(self.status, False, False, 0)
        vb.pack_start(self.detail, False, False, 0)
        row.pack_start(vb, True, True, 0)
        card.pack_start(row, False, False, 0)
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_no_show_all(True)
        card.pack_start(self.progress, False, False, 0)
        btns = Gtk.Box(spacing=8)
        self.b_check = Gtk.Button(label="업데이트 확인")
        self.b_check.get_style_context().add_class("ku-big")
        self.b_check.connect("clicked", lambda *_: self.check())
        self.b_install = Gtk.Button(label="다운로드 및 설치")
        self.b_install.get_style_context().add_class("ku-big")
        self.b_install.get_style_context().add_class("suggested-action")
        self.b_install.connect("clicked", lambda *_: self.install())
        self.b_reboot = Gtk.Button(label="지금 다시 시작")
        self.b_reboot.get_style_context().add_class("ku-big")
        self.b_reboot.connect("clicked", lambda *_: subprocess.Popen(["xfce4-session-logout", "--reboot"]))
        self.b_reboot.set_no_show_all(True)
        btns.pack_start(self.b_check, False, False, 0)
        btns.pack_start(self.b_install, False, False, 0)
        btns.pack_start(self.b_reboot, False, False, 0)
        card.pack_start(btns, False, False, 0)
        outer.pack_start(card, False, False, 0)

        # 목록
        self.list_label = Gtk.Label(label="", xalign=0)
        self.list_label.get_style_context().add_class("ku-muted")
        outer.pack_start(self.list_label, False, False, 0)
        self.store = Gtk.ListStore(str, str, str)
        tv = Gtk.TreeView(model=self.store)
        for i, (title, expand) in enumerate((("이름", True), ("버전", True), ("크기", False))):
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)
            col.set_expand(expand)
            tv.append_column(col)
        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.add(tv)
        outer.pack_start(sw, True, True, 0)

        # 바닥 안내
        auto = "보안 업데이트는 매일 자동으로 확인·설치됩니다." if self._timer_active() else "자동 보안 업데이트가 꺼져 있습니다."
        foot = Gtk.Label(label=auto + "  마지막 확인: " + self._last_check(), xalign=0)
        foot.get_style_context().add_class("ku-muted")
        foot.set_line_wrap(True)
        self.foot = foot
        outer.pack_start(foot, False, False, 0)

        self.show_all()
        GLib.idle_add(self.check)

    # ---------- 상태 ----------
    @staticmethod
    def _timer_active():
        try:
            return subprocess.run(["systemctl", "is-active", "dnf5-automatic.timer"], capture_output=True, text=True).stdout.strip() == "active"
        except OSError:
            return False

    def _last_check(self):
        try:
            with open(os.path.join(STATE_DIR, "last-update-check")) as f:
                return f.read().strip()
        except OSError:
            return "없음"

    def _stamp(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(os.path.join(STATE_DIR, "last-update-check"), "w") as f:
            f.write(now)
        self.foot.set_text(self.foot.get_text().split("  마지막 확인:")[0] + "  마지막 확인: " + now)

    def set_state(self, icon, status, detail="", busy=False):
        self.icon.set_from_icon_name(icon, Gtk.IconSize.DND)
        self.status.set_text(status)
        self.detail.set_text(detail)
        self.busy = busy
        self.b_check.set_sensitive(not busy)
        self.b_install.set_sensitive(not busy and bool(self.updates))
        self.progress.set_visible(busy)

    def _progress_cb(self, progress, ptype, _data=None):
        if ptype == PK.ProgressType.PERCENTAGE:
            pct = progress.get_property("percentage")
            if 0 <= pct <= 100:
                GLib.idle_add(self.progress.set_fraction, pct / 100)
        elif ptype == PK.ProgressType.STATUS:
            st = progress.get_property("status")
            text = {PK.StatusEnum.DOWNLOAD: "다운로드 중", PK.StatusEnum.INSTALL: "설치 중", PK.StatusEnum.UPDATE: "업데이트 적용 중",
                    PK.StatusEnum.REFRESH_CACHE: "업데이트 목록 받는 중", PK.StatusEnum.QUERY: "확인 중",
                    PK.StatusEnum.WAITING_FOR_AUTH: "권한 확인 중", PK.StatusEnum.DEP_RESOLVE: "의존성 계산 중"}.get(st)
            if text:
                GLib.idle_add(self.progress.set_text, text)

    # ---------- 확인 ----------
    def check(self):
        if self.busy:
            return
        self.updates = []
        self.store.clear()
        self.set_state("view-refresh-symbolic", "업데이트를 확인하는 중...", "", busy=True)
        self.progress.set_fraction(0)
        self.progress.set_text("업데이트 목록 받는 중")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        try:
            self.client.refresh_cache(False, None, self._progress_cb, None)
            res = self.client.get_updates(PK.filter_bitfield_from_string("none"), None, self._progress_cb, None)
            pkgs = res.get_package_array()
            items = []
            for p in pkgs:
                items.append((p.get_id(), p.get_name(), p.get_version(), p.get_summary() or ""))
            sizes = {}
            if items:
                try:
                    det = self.client.get_details([i[0] for i in items], None, self._progress_cb, None)
                    for d in det.get_details_array():
                        sizes[d.get_package_id()] = d.get_size()
                except GLib.Error:
                    pass
            GLib.idle_add(self._check_done, items, sizes, None)
        except GLib.Error as e:
            GLib.idle_add(self._check_done, [], {}, str(e))

    def _check_done(self, items, sizes, err):
        self._stamp()
        if err:
            self.set_state("dialog-warning-symbolic", "업데이트를 확인할 수 없습니다", err)
            self.b_install.set_sensitive(False)
            return
        self.updates = [i[0] for i in items]
        total = sum(sizes.get(i[0], 0) for i in items)
        for pid, name, ver, _ in items:
            self.store.append([name, ver, human(sizes[pid]) if pid in sizes else ""])
        if not items:
            self.set_state("emblem-ok-symbolic", "최신 상태입니다", "설치할 시스템 업데이트가 없습니다. Flatpak 앱은 [다운로드 및 설치] 로 갱신할 수 있습니다.")
            self.b_install.set_sensitive(shutil.which("flatpak") is not None)
            self.list_label.set_text("")
        else:
            self.set_state("software-update-available-symbolic", f"업데이트 {len(items)}개를 사용할 수 있습니다",
                           f"다운로드 {human(total)}. [다운로드 및 설치] 를 누르면 시작합니다.")
            self.list_label.set_text("설치할 항목")
        if any(i[1] in REBOOT_PKGS for i in items):
            self.needs_reboot = True

    # ---------- 설치 ----------
    def install(self):
        if self.busy:
            return
        self.set_state("software-update-available-symbolic", "업데이트를 설치하는 중...", "이 창을 닫아도 설치는 계속됩니다.", busy=True)
        self.progress.set_fraction(0)
        self.progress.set_text("준비 중")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        err = None
        try:
            if self.updates:
                self.client.update_packages(PK.TransactionFlagEnum.NONE, self.updates, None, self._progress_cb, None)
        except GLib.Error as e:
            err = str(e)
        flat = ""
        if shutil.which("flatpak"):
            GLib.idle_add(self.progress.set_text, "Flatpak 앱 업데이트 중")
            try:
                r = subprocess.run(["flatpak", "update", "-y", "--noninteractive"], capture_output=True, text=True, timeout=1800)
                flat = "" if r.returncode == 0 else (r.stderr.strip().splitlines() or ["flatpak 오류"])[-1]
            except (OSError, subprocess.SubprocessError) as e:
                flat = str(e)
        GLib.idle_add(self._install_done, err, flat)

    def _install_done(self, err, flat):
        self._stamp()
        self.store.clear()
        self.list_label.set_text("")
        if err:
            self.set_state("dialog-error-symbolic", "업데이트를 설치하지 못했습니다", err)
            return
        self.updates = []
        if self.needs_reboot:
            self.set_state("system-reboot-symbolic", "다시 시작이 필요합니다", "커널 또는 핵심 구성 요소가 갱신되었습니다. 다시 시작하면 적용됩니다." + (f" (Flatpak: {flat})" if flat else ""))
            self.b_reboot.show()
        else:
            self.set_state("emblem-ok-symbolic", "최신 상태입니다", "모든 업데이트를 설치했습니다." + (f" (Flatpak: {flat})" if flat else ""))
        self.b_install.set_sensitive(False)


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.get_active_window() or UpdateWindow(self)
        win.present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
