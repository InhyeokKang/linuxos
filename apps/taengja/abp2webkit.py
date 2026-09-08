#!/usr/bin/python3
"""Adblock Plus 형식 필터(EasyList/EasyPrivacy/List-KR)를 WebKit 콘텐츠 차단기 JSON 으로 변환.

  abp2webkit.py [-o out.json] [--max N] [--no-cosmetic] list1.txt [list2.txt ...]

지원: 네트워크 차단 규칙(||도메인^, |주소, 부분 문자열, * 와일드카드, ^ 구분자), $third-party/~third-party,
      $domain=..., 리소스 종류(script/image/stylesheet/xmlhttprequest/subdocument/font/media/other),
      예외 규칙(@@ — 같은 형태만, ignore-previous-rules), 도메인 한정 요소 숨김(도메인##선택자).
미지원(건너뜀): $redirect/$csp/$removeparam/$important/$match-case/$popup/$websocket/정규식 규칙/일반 요소 숨김 등.
WebKit 은 규칙 수가 많으면 컴파일이 느려지므로 --max 로 상한(기본 45000)을 둔다.
"""
import argparse
import json
import re
import sys

TYPE_MAP = {
    "script": "script", "image": "image", "stylesheet": "style-sheet", "xmlhttprequest": "raw",
    "subdocument": "document", "font": "font", "media": "media", "other": "raw", "object": "raw",
}
SKIP_OPTIONS = {"redirect", "csp", "removeparam", "important", "match-case", "popup", "websocket", "ping",
                "genericblock", "generichide", "badfilter", "rewrite", "replace", "cookie", "denyallow",
                "method", "header", "to", "from", "app", "network", "empty", "mp4", "object-subrequest",
                "webrtc", "xhr", "css", "frame", "doc", "ghide", "ehide", "strict3p", "strict1p", "3p", "1p",
                "all", "inline-script", "inline-font", "elemhide", "document", "urlblock", "generic"}
SEP = r"[^a-zA-Z0-9_.%-]"


def pattern_to_regex(pat):
    """ABP 주소 패턴 → WebKit url-filter 정규식. 변환 불가면 None."""
    if pat.startswith("/") and pat.endswith("/") and len(pat) > 2:
        return None  # 정규식 규칙은 방언 차이가 커서 건너뜀
    anchored_start = anchored_end = False
    domain_anchor = False
    if pat.startswith("||"):
        domain_anchor = True
        pat = pat[2:]
    elif pat.startswith("|"):
        anchored_start = True
        pat = pat[1:]
    if pat.endswith("|"):
        anchored_end = True
        pat = pat[:-1]
    if not pat or "$" in pat:
        return None
    out = []
    for ch in pat.lower():
        if ch == "*":
            out.append(".*")
        elif ch == "^":
            out.append(SEP)
        elif ch in ".+?()[]{}|\\/":
            out.append("\\" + ch)
        elif ch.isalnum() or ch in "-_%&=:,;~!@#'`":
            out.append(ch)
        else:
            return None
    body = "".join(out)
    if domain_anchor:
        body = r"^[a-z][a-z0-9+.-]*://([^/?#]*\.)?" + body
    elif anchored_start:
        body = "^" + body
    if anchored_end:
        body += "$"
    # WebKit 은 아주 짧은 부분 문자열 규칙에 과하게 매칭되므로 3글자 미만은 버림
    if len(pat) < 3:
        return None
    return body


def parse_options(opt_str, exception=False):
    """옵션 문자열 → (trigger 추가 항목, ok). 예외 규칙의 $document/$elemhide 등은 사이트 전체 허용으로 본다."""
    trig = {}
    if not opt_str:
        return trig, True
    types = []
    site_wide = {"document", "elemhide", "generichide", "genericblock", "urlblock", "ehide", "ghide", "doc"}
    for o in opt_str.split(","):
        o = o.strip()
        if not o:
            continue
        if o == "third-party":
            trig["load-type"] = ["third-party"]
        elif o == "~third-party":
            trig["load-type"] = ["first-party"]
        elif o.startswith("domain="):
            inc, exc = [], []
            for d in o[7:].split("|"):
                if d.startswith("~"):
                    exc.append("*" + d[1:].lower())
                elif d:
                    inc.append("*" + d.lower())
            if inc and exc:
                return trig, False  # WebKit 은 if-domain 과 unless-domain 동시 사용 불가
            if inc:
                trig["if-domain"] = inc
            if exc:
                trig["unless-domain"] = exc
        elif exception and o in site_wide:
            continue
        elif o in TYPE_MAP:
            types.append(TYPE_MAP[o])
        elif o.startswith("~") and o[1:] in TYPE_MAP:
            return trig, False
        elif o in SKIP_OPTIONS or o.startswith("~"):
            return trig, False
        else:
            return trig, False
    if types:
        trig["resource-type"] = sorted(set(types))
    return trig, True


def convert_lines(lines, cosmetic=True):
    block, allow, hide = [], [], []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("!") or line.startswith("[") or line.startswith("#"):
            continue
        # 요소 숨김 (도메인 한정만)
        if "##" in line and not line.startswith("@@"):
            dom, sel = line.split("##", 1)
            if "#@#" in line or "#?#" in line or "#$#" in line or not dom or not cosmetic:
                continue
            doms = [("*" + d.lower()) for d in dom.split(",") if d and not d.startswith("~")]
            if not doms or len(sel) > 200 or "\\" in sel:
                continue
            hide.append({"trigger": {"url-filter": ".*", "if-domain": doms},
                         "action": {"type": "css-display-none", "selector": sel}})
            continue
        if "#@#" in line or "#?#" in line or "#$#" in line or "#%#" in line:
            continue
        exception = line.startswith("@@")
        if exception:
            line = line[2:]
        pat, _, opts = line.partition("$")
        regex = pattern_to_regex(pat)
        if regex is None:
            continue
        trig, ok = parse_options(opts, exception)
        if not ok:
            continue
        trig["url-filter"] = regex
        if exception:
            allow.append({"trigger": trig, "action": {"type": "ignore-previous-rules"}})
        else:
            block.append({"trigger": trig, "action": {"type": "block"}})
    return block, hide, allow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--output", default="-")
    ap.add_argument("--max", type=int, default=45000)
    ap.add_argument("--no-cosmetic", action="store_true")
    a = ap.parse_args()
    block, hide, allow = [], [], []
    for f in a.files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            b, h, w = convert_lines(fh, cosmetic=not a.no_cosmetic)
        block += b; hide += h; allow += w
    # 차단 → 숨김 → 예외 순서 (ignore-previous-rules 는 앞선 규칙만 무시)
    budget = a.max - len(allow)
    rules = (block + hide)[:max(budget, 0)] + allow
    data = json.dumps(rules, ensure_ascii=False, separators=(",", ":"))
    if a.output == "-":
        sys.stdout.write(data)
    else:
        with open(a.output, "w", encoding="utf-8") as out:
            out.write(data)
    print(f"block={len(block)} hide={len(hide)} allow={len(allow)} -> {len(rules)} rules", file=sys.stderr)


if __name__ == "__main__":
    main()
