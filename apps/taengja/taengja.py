#!/usr/bin/python3
# 탱자 (taengja) — kiyu 의 웹 브라우저, 프로토타입 (v0)
#
# 엔진: WebKitGTK (Fedora/Debian 이 보안 패치를 배포). 이 파일은 그 위의 "브라우저" 부분:
# 창/탭/주소창, 보안 기본값(샌드박스, 추적 방지, 서드파티 쿠키 차단, 추적기 차단 목록, 권한 기본 거부),
# 저사양 튜닝(탭별 프로세스 수 제한, 메모리 상한, 필요할 때만 GPU), 윈도우/크롬식 단축키, 한국어 UI.
#
# 의존: python3-gobject, gtk3, webkit2gtk4.1 (Fedora) / python3-gi, gir1.2-webkit2-4.1 (Debian)
# 이름: 탱자(trifoliate orange) — kiyu(귤) 의 형제 과일
import json
import os
import sys
import urllib.parse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit2  # noqa: E402

APP_ID = "org.kiyu.Taengja"
APP_NAME = "탱자"
VERSION = "0.1.0"
CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "taengja")
DATA_DIR = os.path.join(GLib.get_user_data_dir(), "taengja")
CACHE_DIR = os.path.join(GLib.get_user_cache_dir(), "taengja")

SEARCH_ENGINES = {
    "duckduckgo": ("DuckDuckGo", "https://duckduckgo.com/?q={}"),
    "naver": ("네이버", "https://search.naver.com/search.naver?query={}"),
    "google": ("Google", "https://www.google.com/search?q={}"),
    "bing": ("Bing", "https://www.bing.com/search?q={}"),
}
DEFAULT_CONFIG = {
    "search": "duckduckgo",
    "homepage": "kiyu:home",
    "block_trackers": True,
    "https_first": True,
    "zoom": 1.0,
}

# 추적기/광고 차단 목록 (WebKit content-blocker 규칙). v0 는 대표적인 추적 도메인만 내장.
# 이후 EasyPrivacy 등을 빌드 시 변환해 /usr/share/taengja/filters.json 로 제공 예정.
TRACKER_DOMAINS = [
    "google-analytics.com", "googletagmanager.com", "googletagservices.com", "googlesyndication.com",
    "doubleclick.net", "googleadservices.com", "adservice.google.com", "connect.facebook.net",
    "facebook.com/tr", "pixel.facebook.com", "analytics.twitter.com", "ads-twitter.com",
    "scorecardresearch.com", "quantserve.com", "hotjar.com", "mouseflow.com", "fullstory.com",
    "crazyegg.com", "mixpanel.com", "segment.io", "segment.com", "amplitude.com", "branch.io",
    "criteo.com", "criteo.net", "taboola.com", "outbrain.com", "adnxs.com", "rubiconproject.com",
    "pubmatic.com", "openx.net", "casalemedia.com", "advertising.com", "adsrvr.org", "bluekai.com",
    "demdex.net", "omtrdc.net", "chartbeat.com", "newrelic.com", "nr-data.net", "bugsnag.com",
    "sentry.io", "yieldmo.com", "smartadserver.com", "adform.net", "moatads.com", "doubleverify.com",
    "adcolony.com", "unityads.unity3d.com", "applovin.com", "appsflyer.com", "adjust.com", "kochava.com",
    "wcs.naver.net", "ad.naver.com", "adcr.naver.com", "veta.naver.com", "log.daum.net", "ad.daum.net",
    "adpnut.com", "adop.cc", "mobon.net", "widerplanet.com", "targetpush.co.kr", "criteo.kr", "dable.io",
]


def _filter_rules():
    rules = []
    for d in TRACKER_DOMAINS:
        esc = d.replace(".", "\\.").replace("/", "\\/")
        rules.append({
            "trigger": {"url-filter": "^https?://([^/]+\\.)?" + esc, "load-type": ["third-party"]},
            "action": {"type": "block"},
        })
    # 서드파티 컨텍스트의 쿠키 차단 (ITP 와 이중 보호)
    rules.append({"trigger": {"url-filter": ".*", "load-type": ["third-party"]},
                  "action": {"type": "block-cookies"}})
    return json.dumps(rules)


HOME_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>새 탭</title>
<style>
 body{margin:0;font-family:"Noto Sans","Noto Sans CJK KR",sans-serif;background:linear-gradient(#f7f3ec,#ebe4d6);
      color:#333;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center}
 .logo{width:96px;height:96px;margin-bottom:18px}
 form{display:flex;width:min(640px,90vw);box-shadow:0 2px 12px rgba(0,0,0,.12);border-radius:28px;overflow:hidden;background:#fff}
 input{flex:1;border:0;padding:14px 20px;font-size:17px;outline:none;background:#fff}
 button{border:0;background:#f47c0c;color:#fff;padding:0 22px;font-size:16px;cursor:pointer}
 p{color:#777;font-size:13px;margin-top:20px}
 .links{margin-top:26px;display:flex;gap:14px}
 .links a{color:#444;text-decoration:none;background:#fff;padding:8px 14px;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
</style></head><body>
<svg class="logo" viewBox="0 0 256 256"><circle cx="128" cy="128" r="122" fill="#f47c0c"/><circle cx="128" cy="128" r="111" fill="#fff3c9"/>
<g fill="#ff9a1c">SEGMENTS</g></svg>
<form action="kiyu:search" method="get"><input name="q" autofocus placeholder="검색어 또는 주소 입력" autocomplete="off"><button>검색</button></form>
<div class="links"><a href="https://www.naver.com">네이버</a><a href="https://www.google.com">Google</a><a href="https://www.youtube.com">YouTube</a><a href="https://namu.wiki">나무위키</a></div>
<p>추적기 차단 · 서드파티 쿠키 차단 · 샌드박스 실행 중</p>
</body></html>"""


def _home_html():
    import math
    segs = []
    for i in range(8):
        th = i * 45 - 90
        a1, a2 = math.radians(th - 16.5), math.radians(th + 16.5)
        r0, r1 = 20, 95
        p = lambda r, a: (128 + r * math.cos(a), 128 + r * math.sin(a))
        p0, p1, p2, p3 = p(r0, a1), p(r1, a1), p(r1, a2), p(r0, a2)
        segs.append(f'<path d="M{p0[0]:.1f} {p0[1]:.1f} L{p1[0]:.1f} {p1[1]:.1f} A{r1} {r1} 0 0 1 {p2[0]:.1f} {p2[1]:.1f} '
                    f'L{p3[0]:.1f} {p3[1]:.1f} A{r0} {r0} 0 0 0 {p0[0]:.1f} {p0[1]:.1f} Z" stroke="#ff9a1c" stroke-width="6" stroke-linejoin="round"/>')
    return HOME_HTML.replace("SEGMENTS", "".join(segs))


class Config:
    def __init__(self):
        self.path = os.path.join(CONFIG_DIR, "config.json")
        self.data = dict(DEFAULT_CONFIG)
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data.update(json.load(f))
        except Exception:
            pass

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v
        self.save()


class Bookmarks:
    def __init__(self):
        self.path = os.path.join(DATA_DIR, "bookmarks.json")
        try:
            with open(self.path, encoding="utf-8") as f:
                self.items = json.load(f)
        except Exception:
            self.items = []

    def toggle(self, title, url):
        before = len(self.items)
        self.items = [b for b in self.items if b["url"] != url]
        added = len(self.items) == before
        if added:
            self.items.append({"title": title or url, "url": url})
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)
        return added

    def has(self, url):
        return any(b["url"] == url for b in self.items)


class Browser(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.config = Config()
        self.bookmarks = Bookmarks()
        self.window = None

    # ---------- WebKit 전역 설정: 보안/자원 ----------
    def _setup_webkit(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        dm = WebKit2.WebsiteDataManager(base_data_directory=DATA_DIR, base_cache_directory=CACHE_DIR)
        # 지능형 추적 방지 (Safari 의 ITP 와 동일 엔진 기능)
        try:
            dm.set_itp_enabled(True)
        except AttributeError:
            pass
        # 저사양: 웹 프로세스 메모리 상한 (초과 시 캐시부터 정리)
        try:
            mp = WebKit2.MemoryPressureSettings()
            mp.set_memory_limit(768)
            mp.set_conservative_threshold(0.5)
            mp.set_strict_threshold(0.85)
            mp.set_kill_threshold(1.5)
            self.context = WebKit2.WebContext.new_with_website_data_manager(dm)  # noqa: F841 (아래서 재생성)
            self.context = WebKit2.WebContext(website_data_manager=dm, memory_pressure_settings=mp)
        except Exception:
            self.context = WebKit2.WebContext.new_with_website_data_manager(dm)
        # 웹 콘텐츠를 bubblewrap 샌드박스 안에서 실행 (파일시스템/네트워크 격리)
        try:
            self.context.set_sandbox_enabled(True)
        except AttributeError:
            pass
        # 쿠키: 서드파티 차단, 디스크 저장
        cm = self.context.get_cookie_manager()
        cm.set_accept_policy(WebKit2.CookieAcceptPolicy.NO_THIRD_PARTY)
        cm.set_persistent_storage(os.path.join(DATA_DIR, "cookies.sqlite"), WebKit2.CookiePersistentStorage.SQLITE)
        self.context.set_cache_model(WebKit2.CacheModel.WEB_BROWSER)
        self.context.set_spell_checking_enabled(False)
        self.context.set_preferred_languages(["ko-KR", "ko", "en-US", "en"])
        # 다운로드
        self.context.connect("download-started", self._on_download_started)
        # kiyu: 내부 스킴 (홈, 검색)
        self.context.register_uri_scheme("kiyu", self._on_kiyu_scheme)
        # 추적기 차단 목록 컴파일 (캐시됨)
        self.content_filter = None
        if self.config["block_trackers"]:
            store = WebKit2.UserContentFilterStore(path=os.path.join(CACHE_DIR, "filters"))
            store.save("kiyu-trackers", GLib.Bytes.new(_filter_rules().encode()), None, self._on_filter_saved)

    def _on_filter_saved(self, store, result):
        try:
            self.content_filter = store.save_finish(result)
            if self.window:
                for view in self.window.views():
                    view.get_user_content_manager().add_filter(self.content_filter)
        except GLib.Error as e:
            print("taengja: 필터 컴파일 실패:", e, file=sys.stderr)

    def _on_kiyu_scheme(self, request):
        uri = request.get_uri()
        path = uri.split(":", 1)[1]
        if path.startswith("search"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(uri).query).get("q", [""])[0]
            request.get_web_view().load_uri(self.search_url(q))
            body = b""
        else:
            body = _home_html().encode()
        stream = Gio.MemoryInputStream.new_from_data(body)
        request.finish(stream, len(body), "text/html; charset=utf-8")

    def _on_download_started(self, context, download):
        download.connect("decide-destination", self._on_decide_destination)
        download.connect("finished", lambda d: self.window and self.window.flash("다운로드 완료: " + os.path.basename(d.get_destination() or "")))
        download.connect("failed", lambda d, e: self.window and self.window.flash("다운로드 실패: " + e.message))

    def _on_decide_destination(self, download, suggested):
        folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or os.path.expanduser("~")
        name = suggested or "download"
        dest = os.path.join(folder, name)
        base, ext = os.path.splitext(dest)
        n = 1
        while os.path.exists(dest):
            dest = f"{base} ({n}){ext}"
            n += 1
        download.set_destination(GLib.filename_to_uri(dest, None))
        if self.window:
            self.window.flash("다운로드 중: " + os.path.basename(dest))
        return True

    # ---------- 주소/검색 ----------
    def search_url(self, q):
        key = self.config["search"] if self.config["search"] in SEARCH_ENGINES else "duckduckgo"
        return SEARCH_ENGINES[key][1].format(urllib.parse.quote_plus(q))

    def resolve(self, text):
        t = text.strip()
        if not t:
            return self.config["homepage"]
        if t.startswith(("http://", "https://", "file://", "kiyu:", "about:")):
            return t
        if " " not in t and ("." in t or t.startswith("localhost")) and not t.endswith("."):
            scheme = "https://" if self.config["https_first"] else "http://"
            return scheme + t
        return self.search_url(t)

    # ---------- 앱 생명주기 ----------
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self._setup_webkit()
        for name, cb, accels in [
            ("new-tab", lambda *_: self.window.new_tab(), ["<Primary>t"]),
            ("close-tab", lambda *_: self.window.close_tab(), ["<Primary>w", "<Primary>F4"]),
            ("next-tab", lambda *_: self.window.cycle_tab(1), ["<Primary>Tab", "<Primary>Page_Down"]),
            ("prev-tab", lambda *_: self.window.cycle_tab(-1), ["<Primary><Shift>Tab", "<Primary>Page_Up"]),
            ("focus-url", lambda *_: self.window.focus_url(), ["<Primary>l", "F6", "<Alt>d"]),
            ("reload", lambda *_: self.window.view().reload(), ["<Primary>r", "F5"]),
            ("stop", lambda *_: self.window.view().stop_loading(), ["Escape"]),
            ("back", lambda *_: self.window.view().go_back(), ["<Alt>Left"]),
            ("forward", lambda *_: self.window.view().go_forward(), ["<Alt>Right"]),
            ("home", lambda *_: self.window.load(self.config["homepage"]), ["<Alt>Home"]),
            ("zoom-in", lambda *_: self.window.zoom(0.1), ["<Primary>plus", "<Primary>equal"]),
            ("zoom-out", lambda *_: self.window.zoom(-0.1), ["<Primary>minus"]),
            ("zoom-reset", lambda *_: self.window.zoom(None), ["<Primary>0"]),
            ("bookmark", lambda *_: self.window.toggle_bookmark(), ["<Primary>d"]),
            ("find", lambda *_: self.window.show_find(), ["<Primary>f", "F3"]),
            ("fullscreen", lambda *_: self.window.toggle_fullscreen(), ["F11"]),
            ("quit", lambda *_: self.quit(), ["<Primary>q", "<Primary><Shift>w"]),
        ]:
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", cb)
            self.add_action(act)
            self.set_accels_for_action("app." + name, accels)

    def do_activate(self):
        if not self.window:
            self.window = BrowserWindow(self)
        self.window.present()
        if not self.window.views():
            self.window.new_tab(self.config["homepage"])

    def do_open(self, files, n, hint):
        self.do_activate()
        for f in files:
            self.window.new_tab(f.get_uri())


class BrowserWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.app = app
        self.set_default_size(1200, 800)
        self.set_icon_name("taengja")
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        toolbar = Gtk.Box(spacing=4, margin=4)
        vbox.pack_start(toolbar, False, False, 0)
        self.back_btn = self._tool_button(toolbar, "go-previous-symbolic", "뒤로 (Alt+←)", "app.back")
        self.fwd_btn = self._tool_button(toolbar, "go-next-symbolic", "앞으로 (Alt+→)", "app.forward")
        self.reload_btn = self._tool_button(toolbar, "view-refresh-symbolic", "새로 고침 (F5)", "app.reload")
        self._tool_button(toolbar, "go-home-symbolic", "홈 (Alt+Home)", "app.home")

        self.url = Gtk.Entry()
        self.url.set_placeholder_text("검색어 또는 주소 입력")
        self.url.set_hexpand(True)
        self.url.connect("activate", lambda e: self.load(self.app.resolve(e.get_text())))
        self.url.connect("icon-press", self._on_url_icon)
        toolbar.pack_start(self.url, True, True, 0)

        self.bm_btn = self._tool_button(toolbar, "non-starred-symbolic", "북마크 (Ctrl+D)", "app.bookmark")
        self._tool_button(toolbar, "tab-new-symbolic", "새 탭 (Ctrl+T)", "app.new-tab")
        menu_btn = Gtk.MenuButton()
        menu_btn.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        menu_btn.set_tooltip_text("메뉴")
        menu_btn.set_popover(self._build_menu())
        toolbar.pack_start(menu_btn, False, False, 0)

        self.find_bar = Gtk.SearchBar()
        self.find_entry = Gtk.SearchEntry()
        self.find_entry.set_placeholder_text("페이지에서 찾기")
        self.find_entry.connect("search-changed", lambda e: self.view().get_find_controller().search(e.get_text(), WebKit2.FindOptions.CASE_INSENSITIVE | WebKit2.FindOptions.WRAP_AROUND, 500))
        self.find_entry.connect("activate", lambda e: self.view().get_find_controller().search_next())
        self.find_entry.connect("stop-search", lambda e: (self.find_bar.set_search_mode(False), self.view().get_find_controller().search_finish()))
        self.find_bar.add(self.find_entry)
        self.find_bar.connect_entry(self.find_entry)
        vbox.pack_start(self.find_bar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_border(False)
        self.notebook.connect("switch-page", self._on_switch_page)
        self.notebook.connect("page-removed", lambda *_: GLib.idle_add(self._after_tab_removed))
        vbox.pack_start(self.notebook, True, True, 0)

        self.status = Gtk.Label(xalign=0, margin_start=6)
        self.status.set_ellipsize(3)
        self.status.get_style_context().add_class("dim-label")
        self.progress = Gtk.ProgressBar()
        self.progress.set_no_show_all(True)
        vbox.pack_start(self.progress, False, False, 0)
        vbox.pack_start(self.status, False, False, 2)
        self.status.set_no_show_all(True)

        self.connect("key-press-event", self._on_key)
        self.show_all()

    def _build_menu(self):
        pop = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=8, spacing=4)
        pop.add(box)

        zoom_box = Gtk.Box(spacing=4)
        zoom_box.pack_start(Gtk.Label(label="확대"), False, False, 4)
        for label, delta in (("−", -0.1), ("100%", None), ("+", 0.1)):
            b = Gtk.Button(label=label)
            b.connect("clicked", lambda _b, d=delta: self.zoom(d))
            zoom_box.pack_start(b, True, True, 0)
        box.pack_start(zoom_box, False, False, 0)
        box.pack_start(Gtk.Separator(), False, False, 4)

        engine_box = Gtk.Box(spacing=4)
        engine_box.pack_start(Gtk.Label(label="검색 엔진"), False, False, 4)
        combo = Gtk.ComboBoxText()
        for key, (name, _) in SEARCH_ENGINES.items():
            combo.append(key, name)
        combo.set_active_id(self.app.config["search"])
        combo.connect("changed", lambda c: self.app.config.__setitem__("search", c.get_active_id()))
        engine_box.pack_start(combo, True, True, 0)
        box.pack_start(engine_box, False, False, 0)

        for label, key in (("추적기 차단", "block_trackers"), ("HTTPS 우선", "https_first")):
            sw = Gtk.CheckButton(label=label)
            sw.set_active(self.app.config[key])
            sw.connect("toggled", lambda s, k=key: self.app.config.__setitem__(k, s.get_active()))
            box.pack_start(sw, False, False, 0)
        box.pack_start(Gtk.Separator(), False, False, 4)

        self.bm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(Gtk.Label(label="북마크", xalign=0), False, False, 0)
        box.pack_start(self.bm_box, False, False, 0)
        box.pack_start(Gtk.Separator(), False, False, 4)

        for label, action in (("다운로드 폴더 열기", self._open_downloads), ("탱자 정보", self._about)):
            b = Gtk.ModelButton(text=label)
            b.connect("clicked", lambda _b, a=action: (pop.popdown(), a()))
            box.pack_start(b, False, False, 0)
        pop.connect("show", lambda *_: self._refresh_bookmarks())
        box.show_all()
        return pop

    def _refresh_bookmarks(self):
        for c in self.bm_box.get_children():
            self.bm_box.remove(c)
        for bm in self.app.bookmarks.items[-12:]:
            b = Gtk.ModelButton(text=bm["title"][:48])
            b.connect("clicked", lambda _b, u=bm["url"]: self.load(u))
            self.bm_box.pack_start(b, False, False, 0)
        if not self.app.bookmarks.items:
            self.bm_box.pack_start(Gtk.Label(label="(없음, Ctrl+D 로 추가)", xalign=0), False, False, 0)
        self.bm_box.show_all()

    def _tool_button(self, box, icon, tip, action):
        b = Gtk.Button()
        b.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        b.set_tooltip_text(tip)
        b.set_action_name(action)
        b.set_relief(Gtk.ReliefStyle.NONE)
        box.pack_start(b, False, False, 0)
        return b

    def _open_downloads(self):
        folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or os.path.expanduser("~")
        Gtk.show_uri_on_window(self, GLib.filename_to_uri(folder, None), Gdk.CURRENT_TIME)

    def _about(self):
        d = Gtk.AboutDialog(transient_for=self, program_name=APP_NAME, version=VERSION,
                            comments=f"WebKitGTK {WebKit2.get_major_version()}.{WebKit2.get_minor_version()}.{WebKit2.get_micro_version()} 엔진\n"
                                     "샌드박스, 추적 방지, 서드파티 쿠키 차단, 추적기 차단 기본 적용",
                            website="https://github.com/inhyeokkang/linuxos", logo_icon_name="taengja")
        d.run()
        d.destroy()

    # ---------- 탭 ----------
    def views(self):
        return [self.notebook.get_nth_page(i) for i in range(self.notebook.get_n_pages())]

    def view(self):
        return self.notebook.get_nth_page(self.notebook.get_current_page())

    def new_tab(self, uri=None, related=None):
        if related is not None:
            view = WebKit2.WebView(related_view=related)
        else:
            view = WebKit2.WebView(web_context=self.app.context)
        s = view.get_settings()
        s.set_enable_developer_extras(False)
        s.set_enable_javascript(True)
        s.set_enable_webgl(True)
        s.set_enable_media_stream(True)
        s.set_enable_smooth_scrolling(True)
        s.set_enable_page_cache(True)
        s.set_javascript_can_open_windows_automatically(False)
        s.set_allow_file_access_from_file_urls(False)
        s.set_enable_dns_prefetching(False)
        s.set_enable_site_specific_quirks(True)
        s.set_enable_back_forward_navigation_gestures(True)
        s.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ON_DEMAND)
        s.set_default_font_family("Noto Sans")
        s.set_default_charset("utf-8")
        s.set_user_agent_with_application_details("Taengja", VERSION)
        view.set_zoom_level(self.app.config["zoom"])
        if self.app.content_filter is not None:
            view.get_user_content_manager().add_filter(self.app.content_filter)

        view.connect("notify::title", lambda v, _p: self._update_tab(v))
        view.connect("notify::uri", lambda v, _p: self._update_tab(v))
        view.connect("notify::estimated-load-progress", self._on_progress)
        view.connect("notify::is-loading", lambda v, _p: self._update_tab(v))
        view.connect("notify::favicon", lambda v, _p: self._update_tab(v))
        view.connect("mouse-target-changed", self._on_hover)
        view.connect("create", self._on_create)
        view.connect("decide-policy", self._on_decide_policy)
        view.connect("permission-request", self._on_permission)
        view.connect("load-failed-with-tls-errors", self._on_tls_error)
        view.connect("close", lambda v: self.close_tab(v))
        view.connect("web-process-terminated", lambda v, r: self.flash("페이지가 응답하지 않아 다시 불러옵니다") or v.reload())

        label = self._tab_label(view)
        view.show()
        idx = self.notebook.append_page(view, label)
        self.notebook.set_tab_reorderable(view, True)
        self.notebook.set_current_page(idx)
        if uri:
            view.load_uri(uri)
        self.url.grab_focus()
        return view

    def _tab_label(self, view):
        box = Gtk.Box(spacing=6)
        icon = Gtk.Image.new_from_icon_name("text-html-symbolic", Gtk.IconSize.MENU)
        title = Gtk.Label(label="새 탭")
        title.set_ellipsize(3)
        title.set_width_chars(16)
        title.set_max_width_chars(20)
        title.set_xalign(0)
        close = Gtk.Button()
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.set_image(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU))
        close.connect("clicked", lambda _b: self.close_tab(view))
        box.pack_start(icon, False, False, 0)
        box.pack_start(title, True, True, 0)
        box.pack_start(close, False, False, 0)
        box.show_all()
        view._tab = (icon, title)
        return box

    def _update_tab(self, view):
        icon, title = view._tab
        title.set_text(view.get_title() or view.get_uri() or "새 탭")
        fav = view.get_favicon()
        if fav is not None:
            try:
                pb = Gdk.pixbuf_get_from_surface(fav, 0, 0, fav.get_width(), fav.get_height()).scale_simple(16, 16, 2)
                icon.set_from_pixbuf(pb)
            except Exception:
                pass
        if view is self.view():
            self._sync_chrome(view)

    def _sync_chrome(self, view):
        uri = view.get_uri() or ""
        shown = "" if uri.startswith("kiyu:") else uri
        if not self.url.has_focus():
            self.url.set_text(shown)
        self.set_title(f"{view.get_title() or shown or '새 탭'} — {APP_NAME}")
        self.back_btn.set_sensitive(view.can_go_back())
        self.fwd_btn.set_sensitive(view.can_go_forward())
        self.reload_btn.set_image(Gtk.Image.new_from_icon_name(
            "process-stop-symbolic" if view.is_loading() else "view-refresh-symbolic", Gtk.IconSize.BUTTON))
        self.reload_btn.set_action_name("app.stop" if view.is_loading() else "app.reload")
        self.url.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY,
                                         "channel-secure-symbolic" if uri.startswith("https://") else ("channel-insecure-symbolic" if uri.startswith("http://") else None))
        self.bm_btn.set_image(Gtk.Image.new_from_icon_name(
            "starred-symbolic" if self.app.bookmarks.has(uri) else "non-starred-symbolic", Gtk.IconSize.BUTTON))

    def _on_switch_page(self, nb, page, idx):
        self._sync_chrome(page)

    def _after_tab_removed(self):
        if self.notebook.get_n_pages() == 0:
            self.app.quit()
        return False

    def close_tab(self, view=None):
        view = view or self.view()
        idx = self.notebook.page_num(view)
        if idx >= 0:
            self.notebook.remove_page(idx)
            view.destroy()

    def cycle_tab(self, step):
        n = self.notebook.get_n_pages()
        self.notebook.set_current_page((self.notebook.get_current_page() + step) % n)

    # ---------- 동작 ----------
    def load(self, uri):
        self.view().load_uri(uri)
        self.view().grab_focus()

    def focus_url(self):
        self.url.grab_focus()
        self.url.select_region(0, -1)

    def zoom(self, delta):
        z = 1.0 if delta is None else max(0.3, min(3.0, round(self.view().get_zoom_level() + delta, 2)))
        for v in self.views():
            v.set_zoom_level(z)
        self.app.config["zoom"] = z
        self.flash(f"확대 {int(z * 100)}%")

    def toggle_bookmark(self):
        v = self.view()
        uri = v.get_uri()
        if not uri or uri.startswith("kiyu:"):
            return
        added = self.app.bookmarks.toggle(v.get_title(), uri)
        self.flash("북마크에 추가했습니다" if added else "북마크에서 제거했습니다")
        self._sync_chrome(v)

    def show_find(self):
        self.find_bar.set_search_mode(True)
        self.find_entry.grab_focus()

    def toggle_fullscreen(self):
        if self.get_window().get_state() & Gdk.WindowState.FULLSCREEN:
            self.unfullscreen()
        else:
            self.fullscreen()

    def flash(self, text, seconds=3):
        self.status.set_text(text)
        self.status.show()
        GLib.timeout_add_seconds(seconds, lambda: self.status.hide() or False)

    # ---------- 시그널 ----------
    def _on_progress(self, view, _p):
        if view is not self.view():
            return
        p = view.get_estimated_load_progress()
        if view.is_loading() and p < 1.0:
            self.progress.set_fraction(p)
            self.progress.show()
        else:
            self.progress.hide()
        self._sync_chrome(view)

    def _on_hover(self, view, hit, mods):
        if hit.context_is_link():
            self.status.set_text(hit.get_link_uri())
            self.status.show()
        else:
            self.status.hide()

    def _on_create(self, view, nav):
        # 새 창 요청(target=_blank 등)은 새 탭으로. 팝업 광고는 JS 자동 열기 차단으로 이미 걸러짐.
        return self.new_tab(related=view)

    def _on_decide_policy(self, view, decision, dtype):
        if dtype == WebKit2.PolicyDecisionType.RESPONSE:
            resp = decision.get_response()
            if not decision.is_mime_type_supported():
                decision.download()
                return True
        elif dtype == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            action = decision.get_navigation_action()
            uri = action.get_request().get_uri()
            # 브라우저 밖 스킴(mailto, tel 등)은 시스템 기본 앱으로
            if uri.split(":", 1)[0] in ("mailto", "tel", "magnet", "sms"):
                Gtk.show_uri_on_window(self, uri, Gdk.CURRENT_TIME)
                decision.ignore()
                return True
        return False

    def _on_permission(self, view, request):
        # 위치/알림/장치 정보는 기본 거부. 카메라·마이크는 사용자에게 묻는다.
        if isinstance(request, WebKit2.UserMediaPermissionRequest):
            what = "카메라" if request.props.is_for_video_device else "마이크"
            d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                  buttons=Gtk.ButtonsType.YES_NO,
                                  text=f"{urllib.parse.urlparse(view.get_uri() or '').hostname} 에서 {what} 사용을 요청합니다. 허용할까요?")
            ok = d.run() == Gtk.ResponseType.YES
            d.destroy()
            (request.allow if ok else request.deny)()
        else:
            request.deny()
        return True

    def _on_tls_error(self, view, uri, cert, errors):
        # 인증서 오류: 페이지를 열지 않고 안내 (예외 허용은 v1 에서 명시적 UI 로)
        host = urllib.parse.urlparse(uri).hostname
        view.load_alternate_html(
            f"<html lang='ko'><body style='font-family:Noto Sans,sans-serif;padding:40px;color:#333'>"
            f"<h2>안전하지 않은 연결</h2><p><b>{host}</b> 의 보안 인증서를 확인할 수 없어 페이지를 열지 않았습니다.</p>"
            f"<p style='color:#777'>공용 Wi-Fi 의 로그인 페이지이거나, 사이트 설정 문제이거나, 누군가 연결을 가로채고 있을 수 있습니다.</p></body></html>",
            uri, None)
        return True

    def _on_url_icon(self, entry, pos, event):
        uri = self.view().get_uri() or ""
        if uri.startswith("https://"):
            self.flash("이 연결은 암호화되어 있습니다 (HTTPS)")
        elif uri.startswith("http://"):
            self.flash("이 연결은 암호화되지 않았습니다. 비밀번호를 입력하지 마세요.")

    def _on_key(self, widget, event):
        # 마우스 뒤로/앞으로 버튼은 WebKit 이 처리. 여기서는 Ctrl+숫자 탭 이동만.
        if event.state & Gdk.ModifierType.CONTROL_MASK and Gdk.KEY_1 <= event.keyval <= Gdk.KEY_9:
            n = event.keyval - Gdk.KEY_1
            if event.keyval == Gdk.KEY_9:
                n = self.notebook.get_n_pages() - 1
            if n < self.notebook.get_n_pages():
                self.notebook.set_current_page(n)
            return True
        return False


if __name__ == "__main__":
    GLib.set_prgname("taengja")
    GLib.set_application_name(APP_NAME)
    sys.exit(Browser().run(sys.argv))
