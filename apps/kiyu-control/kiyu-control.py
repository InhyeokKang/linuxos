#!/usr/bin/python3
"""kiyu 빠른 설정 (Quick settings).

패널 오른쪽 알약의 버튼을 누르면 화면 오른쪽 아래에 뜨는 작은 창 하나로
Wi-Fi / 블루투스 / 다크 모드 / 효과(블러) 토글, 소리·밝기 슬라이더, 배터리를 다룬다.
상주하지 않는다: 열려 있을 때만 프로세스가 살아 있고 포커스를 잃으면 종료된다.
외부 도구: nmcli, bluetoothctl(rfkill), pactl, brightnessctl(없으면 /sys/class/backlight), xfconf-query.
"""
import glob
import os
import shutil
import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

STATE_DIR = os.path.join(GLib.get_user_config_dir(), "kiyu")
MARGIN = 10
PANEL_H = 46 + MARGIN


def run(cmd, timeout=3):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def spawn(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def state(name, default=""):
    try:
        with open(os.path.join(STATE_DIR, name)) as f:
            return f.read().strip()
    except OSError:
        return default


def set_state(name, value):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, name), "w") as f:
        f.write(value + "\n")


# ---------- 시스템 상태 ----------
def wifi_status():
    if not shutil.which("nmcli"):
        return None, ""
    on = run(["nmcli", "-t", "radio", "wifi"]) == "enabled"
    ssid = ""
    if on:
        for line in run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"]).splitlines():
            if line.startswith("yes:"):
                ssid = line[4:]
                break
    return on, ssid or ("연결 안 됨" if on else "꺼짐")


def wifi_set(on):
    spawn(["nmcli", "radio", "wifi", "on" if on else "off"])


def bt_status():
    if not shutil.which("bluetoothctl"):
        return None, ""
    out = run(["bluetoothctl", "show"])
    if "Controller" not in out:
        return None, ""
    on = "Powered: yes" in out
    return on, "켜짐" if on else "꺼짐"


def bt_set(on):
    spawn(["bluetoothctl", "power", "on" if on else "off"])


def volume_get():
    out = run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    vol = 0
    for tok in out.replace("/", " ").split():
        if tok.endswith("%"):
            try:
                vol = int(tok[:-1])
                break
            except ValueError:
                pass
    muted = "yes" in run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
    return vol, muted


def volume_set(v):
    spawn(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(v)}%"])


def mute_toggle():
    spawn(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])


def backlight_path():
    for p in sorted(glob.glob("/sys/class/backlight/*")):
        if os.path.exists(os.path.join(p, "brightness")):
            return p
    return None


def brightness_get():
    p = backlight_path()
    if not p:
        return None
    try:
        cur = int(open(os.path.join(p, "brightness")).read())
        mx = int(open(os.path.join(p, "max_brightness")).read())
        return round(cur * 100 / max(mx, 1))
    except (OSError, ValueError):
        return None


def brightness_set(v):
    if shutil.which("brightnessctl"):
        spawn(["brightnessctl", "-q", "set", f"{int(v)}%"])
    else:
        spawn(["xfconf-query", "-c", "xfce4-power-manager", "-p", "/xfce4-power-manager/brightness-level-on-ac",
               "-n", "-t", "int", "-s", str(int(v))])


def battery():
    for p in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        try:
            cap = int(open(os.path.join(p, "capacity")).read())
            st = open(os.path.join(p, "status")).read().strip()
        except (OSError, ValueError):
            continue
        return cap, st
    return None


def dark_get():
    return state("theme", "light") == "dark"


def dark_set(on):
    spawn(["/usr/lib/kiyu/theme", "dark" if on else "light"])


def effects_get():
    return state("effects", "off") == "on"


def effects_set(on):
    set_state("effects", "on" if on else "off")
    spawn(["/usr/lib/kiyu/compositor"])


# ---------- UI ----------
CSS = b"""
#kiyu-control { border-radius: 18px; }
.kc-tile { border-radius: 14px; padding: 10px 12px; min-height: 44px; }
.kc-tile.on { background-color: @kiyu_accent; color: #ffffff; border-color: @kiyu_accent_dark; }
.kc-tile.on label { color: #ffffff; }
.kc-tile .sub { font-size: 85%; opacity: 0.75; }
.kc-title { font-weight: 600; }
.kc-row { padding: 2px 4px; }
"""


class Tile(Gtk.Button):
    def __init__(self, icon, title, on_toggle):
        super().__init__()
        self.get_style_context().add_class("kc-tile")
        self.on_toggle = on_toggle
        self.active = False
        box = Gtk.Box(spacing=10)
        self.img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.title = Gtk.Label(label=title, xalign=0)
        self.title.get_style_context().add_class("kc-title")
        self.sub = Gtk.Label(label="", xalign=0)
        self.sub.get_style_context().add_class("sub")
        vb.pack_start(self.title, False, False, 0)
        vb.pack_start(self.sub, False, False, 0)
        box.pack_start(self.img, False, False, 0)
        box.pack_start(vb, True, True, 0)
        self.add(box)
        self.connect("clicked", self._clicked)

    def set_active(self, on, sub=""):
        self.active = bool(on)
        ctx = self.get_style_context()
        if self.active:
            ctx.add_class("on")
        else:
            ctx.remove_class("on")
        self.sub.set_text(sub)

    def _clicked(self, *_):
        self.set_active(not self.active, self.sub.get_text())
        self.on_toggle(self.active)
        if hasattr(self, "refresh_cb"):
            GLib.timeout_add(900, self.refresh_cb)


class Control(Gtk.Window):
    def __init__(self):
        super().__init__(title="빠른 설정", type=Gtk.WindowType.TOPLEVEL)
        self.set_name("kiyu-control")
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_resizable(False)
        self.set_default_size(340, -1)
        self.connect("focus-out-event", lambda *_: self.quit())
        self.connect("key-press-event", self._key)
        self.connect("delete-event", lambda *_: self.quit())

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)  # 사용자 gtk.css 보다 우선

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=16)
        self.add(outer)

        # 헤더: 사용자 / 설정 / 잠금 / 전원
        head = Gtk.Box(spacing=8)
        av = Gtk.Image.new_from_icon_name("avatar-default-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        name = Gtk.Label(label=GLib.get_real_name() or GLib.get_user_name(), xalign=0)
        name.get_style_context().add_class("kc-title")
        head.pack_start(av, False, False, 0)
        head.pack_start(name, True, True, 0)
        for icon, tip, cmd in (("preferences-system-symbolic", "모든 설정", ["xfce4-settings-manager"]),
                               ("system-lock-screen-symbolic", "잠금", ["xflock4"]),
                               ("system-shutdown-symbolic", "전원", ["xfce4-session-logout"])):
            b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            b.get_style_context().add_class("flat")
            b.set_tooltip_text(tip)
            b.connect("clicked", lambda _b, c=cmd: (spawn(c), self.quit()))
            head.pack_start(b, False, False, 0)
        outer.pack_start(head, False, False, 0)

        # 토글 타일 2x2
        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
        self.t_wifi = Tile("network-wireless-symbolic", "Wi-Fi", wifi_set)
        self.t_bt = Tile("bluetooth-active-symbolic", "블루투스", bt_set)
        self.t_dark = Tile("weather-clear-night-symbolic", "다크 모드", dark_set)
        self.t_fx = Tile("preferences-desktop-theme-symbolic", "효과", effects_set)
        self.t_wifi.refresh_cb = self.refresh_wifi
        self.t_bt.refresh_cb = self.refresh_bt
        grid.attach(self.t_wifi, 0, 0, 1, 1)
        grid.attach(self.t_bt, 1, 0, 1, 1)
        grid.attach(self.t_dark, 0, 1, 1, 1)
        grid.attach(self.t_fx, 1, 1, 1, 1)
        outer.pack_start(grid, False, False, 0)

        # 슬라이더
        self.vol = self._slider(outer, "audio-volume-high-symbolic", volume_set, mute_toggle)
        self.bri = self._slider(outer, "display-brightness-symbolic", brightness_set, None)

        # 배터리
        self.bat = Gtk.Box(spacing=8)
        self.bat.get_style_context().add_class("kc-row")
        self.bat_img = Gtk.Image.new_from_icon_name("battery-good-symbolic", Gtk.IconSize.BUTTON)
        self.bat_lbl = Gtk.Label(label="", xalign=0)
        self.bat.pack_start(self.bat_img, False, False, 0)
        self.bat.pack_start(self.bat_lbl, True, True, 0)
        outer.pack_start(self.bat, False, False, 0)

        self.show_all()
        self.refresh_all()
        self._place()
        self.present()

    def _slider(self, parent, icon, setter, on_icon_click):
        row = Gtk.Box(spacing=8)
        row.get_style_context().add_class("kc-row")
        if on_icon_click:
            b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            b.get_style_context().add_class("flat")
            b.connect("clicked", lambda *_: (on_icon_click(), GLib.timeout_add(300, self.refresh_volume)))
            row.pack_start(b, False, False, 0)
            row.icon = b
        else:
            img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            row.pack_start(img, False, False, 0)
            row.icon = img
        sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        sc.set_draw_value(False)
        sc.set_hexpand(True)
        sc.connect("value-changed", lambda s: setter(s.get_value()) if not getattr(s, "_quiet", False) else None)
        row.pack_start(sc, True, True, 0)
        row.scale = sc
        parent.pack_start(row, False, False, 0)
        return row

    @staticmethod
    def _set_quiet(scale, v):
        scale._quiet = True
        scale.set_value(v)
        scale._quiet = False

    def refresh_wifi(self):
        on, sub = wifi_status()
        self.t_wifi.set_visible(on is not None)
        if on is not None:
            self.t_wifi.set_active(on, sub)
        return False

    def refresh_bt(self):
        on, sub = bt_status()
        self.t_bt.set_visible(on is not None)
        if on is not None:
            self.t_bt.set_active(on, sub)
        return False

    def refresh_volume(self):
        v, muted = volume_get()
        self._set_quiet(self.vol.scale, v)
        icon = "audio-volume-muted-symbolic" if muted or v == 0 else \
            "audio-volume-low-symbolic" if v < 34 else "audio-volume-medium-symbolic" if v < 67 else "audio-volume-high-symbolic"
        self.vol.icon.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        return False

    def refresh_all(self):
        self.refresh_wifi()
        self.refresh_bt()
        self.t_dark.set_active(dark_get(), "어두운 화면" if dark_get() else "밝은 화면")
        self.t_fx.set_active(effects_get(), "유리 블러 켜짐" if effects_get() else "가벼운 효과")
        self.refresh_volume()
        b = brightness_get()
        self.bri.set_visible(b is not None)
        if b is not None:
            self._set_quiet(self.bri.scale, b)
        bat = battery()
        self.bat.set_visible(bat is not None)
        if bat:
            cap, st = bat
            level = "full" if cap > 90 else "good" if cap > 55 else "low" if cap > 20 else "caution"
            self.bat_img.set_from_icon_name(f"battery-{level}{'-charging' if st == 'Charging' else ''}-symbolic", Gtk.IconSize.BUTTON)
            self.bat_lbl.set_text(f"배터리 {cap}%" + (" · 충전 중" if st == "Charging" else ""))

    def _place(self):
        disp = Gdk.Display.get_default()
        mon = disp.get_primary_monitor() or disp.get_monitor(0)
        geo = mon.get_geometry()
        w, h = self.get_size()
        self.move(geo.x + geo.width - w - MARGIN, geo.y + geo.height - h - PANEL_H)

    def _key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.quit()

    def quit(self, *_):
        Gtk.main_quit()


def main():
    # 이미 떠 있으면 닫기(토글 동작)
    lock = os.path.join(GLib.get_user_runtime_dir(), "kiyu-control.pid")
    try:
        pid = int(open(lock).read())
        if os.path.exists(f"/proc/{pid}") and "kiyu-control" in open(f"/proc/{pid}/cmdline").read():
            os.kill(pid, 15)
            os.unlink(lock)
            return 0
    except (OSError, ValueError):
        pass
    with open(lock, "w") as f:
        f.write(str(os.getpid()))
    Control()
    Gtk.main()
    try:
        os.unlink(lock)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
