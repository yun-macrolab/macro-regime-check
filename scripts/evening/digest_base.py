#!/usr/bin/env python3
"""저녁판 밑바탕 — 시각·판 날짜·수집 창, 주소·id·열쇠, 여러 단계가 같이 쓰는 규칙, 닫힌 글자 검사, 읽고 쓰기 (2026-10-08).

digest_schema.py(형태와 검증)의 아래층이다. 다른 스크립트는 이 파일을 직접 부르지 않고 digest_schema에서 꺼내 쓴다
(import digest_schema as S 하나면 된다 — 여기 있는 것도 S.collect_window처럼 그대로 나온다). 숫자와 낱말은 digest_rules.py에만 있다.

  시각       iso · parse_iso · edition_date · collect_window · state_base · next_state · in_window · rate_fits
  만드는 법  post_url · item_id · key_of · primary_key · title_sha · page_title
  같이 쓰는 규칙  seed_of(씨앗 글) · pick_links(링크 순서) · coverage_verdict(수집 판정)
  글자 검사  is_closed · closed_violations — 공개본의 모든 문자열이 허용 목록으로 다시 조립되는가
  읽고 쓰기  read_json · write_json · dump · report(개수만 찍는 로그) · run_cli(예외 종류 이름만 찍는다)
  검증 도구  _obj · _arr · _enum … — 오류 메시지에 값을 넣지 않는다(값에 원문이 섞여 있을 수 있다)
"""
import copy
import datetime
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
from html.parser import HTMLParser

import digest_rules as R

SCHEMA = 1
TH = R.TH
KST = datetime.timezone(datetime.timedelta(hours=9))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(REPO, "data")
WORK = os.path.join(REPO, ".work", "evening")

_HANDLE = r"[A-Za-z][A-Za-z0-9_]{3,31}"
HANDLE_RE = re.compile(rf"^{_HANDLE}$")
# 숫자 글자는 0~9뿐이다(re.ASCII) — \d는 다른 문자의 숫자 글자도 받아, 그런 글자가 날짜·주소·id 꼴로 닫힌 글자 검사를 지나간다
URL_RE = re.compile(rf"^https://t\.me/(?P<ch>{_HANDLE})/(?P<id>[1-9]\d{{0,9}})$", re.ASCII)
ID_RE = re.compile(rf"^(?P<d>\d{{8}})-(?P<ch>{_HANDLE})-(?P<id>[1-9]\d{{0,9}})$", re.ASCII)
KEY_KINDS = ("f", "u", "t", "n", "k", "g")     # 전달 · 주소 · 카드 제목 · 숫자 · 주제 · 글 지문(혼자인 묶음 포함) — 대표 열쇠의 우선순위
KEY_RE = re.compile(r"^[futnkg]:[0-9a-f]{12}$")
SHA_RE = re.compile(r"^[0-9a-f]{16}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$", re.ASCII)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$", re.ASCII)
HHMM_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$", re.ASCII)
PAGE_FILE_RE = re.compile(rf"^{_HANDLE}-[1-9]\.html$", re.ASCII)
MAX_POST, MAX_TEXT, MAX_URL = 9_999_999_999, 20_000, 2_000

# ---------- 검증 도구 — 메시지에 값을 넣지 않는다 ----------

FIELDS, WORDS = set(), set(R.TENORS)        # 형태에 나오는 칸 이름 · 닫힌 낱말(코드·사전 낱말) — closed_violations가 쓴다


def _fail(path, why):
    raise ValueError(f"{path}: {why}")


def _obj(req, opt=None):
    req, opt = dict(req), dict(opt or {})
    FIELDS.update(req, opt)

    def check(v, path):
        if type(v) is not dict:
            _fail(path, "객체가 아님")
        if any(k not in req and k not in opt for k in v):
            _fail(path, "정해지지 않은 칸이 있음")
        for k in req:
            if k not in v:
                _fail(f"{path}.{k}", "칸이 없음")
        for k, c in {**req, **opt}.items():
            if k in v:
                c(v[k], f"{path}.{k}")
    return check


def _arr(item, hi, lo=0):
    def check(v, path):
        if type(v) is not list:
            _fail(path, "목록이 아님")
        if not lo <= len(v) <= hi:
            _fail(path, f"개수가 {lo}~{hi} 밖")
        for i, x in enumerate(v):
            item(x, f"{path}[{i}]")
    return check


def _map(item, hi):
    """채널 이름 → 값."""
    def check(v, path):
        if type(v) is not dict or len(v) > hi:
            _fail(path, "객체가 아니거나 너무 큼")
        for k, x in v.items():
            if not (isinstance(k, str) and HANDLE_RE.fullmatch(k)):
                _fail(path, "채널 이름 꼴이 아닌 칸이 있음")
            item(x, f"{path}.{k}")
    return check


def _enum(*vals):
    WORDS.update(vals)

    def check(v, path):
        if not (isinstance(v, str) and v in vals):
            _fail(path, "정해진 값이 아님")
    return check


def _re(rx, why):
    def check(v, path):
        if not (isinstance(v, str) and rx.fullmatch(v)):
            _fail(path, why)
    return check


def _int(lo, hi):
    def check(v, path):
        if type(v) is not int or not lo <= v <= hi:
            _fail(path, f"{lo}~{hi}의 정수가 아님")
    return check


def _num(lo, hi):
    def check(v, path):
        if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi or round(v, 3) != v:
            _fail(path, f"{lo}~{hi}의 수(소수 셋째 자리까지)가 아님")
    return check


def _is(val):
    def check(v, path):
        if type(v) is not type(val) or v != val:
            _fail(path, "정해진 값이 아님")
    return check


def _null(c):
    return lambda v, path: None if v is None else c(v, path)


def _bool(v, path):
    if type(v) is not bool:
        _fail(path, "참·거짓이 아님")


def _text(hi):
    """원문 칸 — <work> 안의 형태에만 쓴다."""
    def check(v, path):
        if not isinstance(v, str) or len(v) > hi:
            _fail(path, "문자열이 아니거나 너무 김")
    return check


def _iso(v, path):
    if not (isinstance(v, str) and ISO_RE.fullmatch(v)):
        _fail(path, "시각 꼴(YYYY-MM-DDTHH:MM:SS+09:00)이 아님")
    try:
        datetime.datetime.fromisoformat(v)
    except ValueError:
        _fail(path, "없는 시각")


def _date(v, path):
    if not (isinstance(v, str) and DATE_RE.fullmatch(v)):
        _fail(path, "날짜 꼴(YYYY-MM-DD)이 아님")
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        _fail(path, "없는 날짜")


def _phrase(v, path):
    if not R.is_phrase(v):
        _fail(path, "고정 문구가 아님")


def _detail(v, path):
    if not (isinstance(v, str) and (v in R.TENORS or R.is_num(v))):
        _fail(path, "만기 낱말이나 숫자+단위가 아님")


def _label(v, path):
    ok = isinstance(v, str) and 0 < len(v) <= 40 and v == v.strip() and unicodedata.normalize("NFC", v) == v
    if not ok or re.search(r"[<>@\\]|https?:|[\x00-\x1f\x7f]", v) or any(unicodedata.category(c) == "Cf" for c in v):
        _fail(path, "라벨 꼴이 아님(1~40자, 태그·주소·보이지 않는 문자 없음)")


def _unique(xs, path, what):
    if len(set(xs)) != len(xs):
        _fail(path, f"{what}이(가) 겹침")


# ---------- 시각 · 판 날짜 · 수집 창 ----------


def iso(dt):
    """시각 → "YYYY-MM-DDTHH:MM:SS+09:00". 시간대 없는 시각은 받지 않는다."""
    if not isinstance(dt, datetime.datetime) or dt.tzinfo is None:
        raise ValueError("시간대가 있는 시각이 아님")
    return dt.astimezone(KST).replace(microsecond=0).isoformat()


def parse_iso(s):
    """ISO 문자열 → 시간대가 있는 시각(KST). --now 인자와 자료의 시각 칸에 쓴다."""
    try:
        dt = datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        raise ValueError("시각을 읽을 수 없음") from None
    if dt.tzinfo is None:
        raise ValueError("시각에 시간대가 없음")
    return dt.astimezone(KST)


def _at(day, h, m):
    return datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=KST)


def edition_date(now):
    """판 날짜 = (실행 시각 − 6시간)의 KST 날짜 → "YYYY-MM-DD". 새벽에 늦게 끝난 실행도 전날 판이 된다."""
    return (parse_iso(iso(now)) - datetime.timedelta(hours=TH["edition_shift_h"])).date().isoformat()


def collect_window(now, state=None):
    """수집 창 → {"date", "from", "to", "kind", "capped"}. kind: first(상태 없음, 24시간) · next(직전 판이 제대로 읽은 곳부터) ·
    rerun(같은 판 날짜 — 첫 실행의 시작점 그대로). 96시간 상한은 first·next에만 건다(rerun은 첫 실행 것을 바꾸지 않는다).
    next의 시작점은 직전 판의 read_to('여기까지 제대로 읽었다' — 수집 부족이던 판은 그 앞 판의 것 그대로), 칸이 없으면 창의 끝이다.
    그래서 수집 부족인 날 못 읽은 글은 다음 판이 다시 읽는다(설계 2절: 수집 창은 직전 성공 ~ 지금)."""
    to = parse_iso(iso(now))
    date, ed = edition_date(to), (state or {}).get("edition")
    start, kind = to - datetime.timedelta(hours=TH["window_first_h"]), "first"
    if ed and ed["date"] == date:
        start, kind = parse_iso(ed["window"]["from"]), "rerun"
    elif ed and ed["date"] < date:
        start, kind = parse_iso(ed.get("read_to") or ed["window"]["to"]), "next"
    if start >= to:                                  # 상태가 지금보다 앞선 시각을 가리킨다(시각을 되돌린 재실행) — 첫 실행처럼
        start, kind = to - datetime.timedelta(hours=TH["window_first_h"]), "first"
    floor = to - datetime.timedelta(hours=TH["window_max_h"])
    capped = kind != "rerun" and start < floor
    return {"date": date, "from": iso(floor if capped else start), "to": iso(to), "kind": kind, "capped": capped}


def state_base(state, date):
    """판 날짜 date의 계산이 견줄 '직전 판'의 기록(없으면 None). 같은 날짜를 다시 돌 때는 그 판이 아니라 그 앞 판을 준다 —
    '어제와 같은 주제' 감점, 채널별 마지막 글 번호, 연속 실패·0건 셈은 모두 이것을 기준으로 다시 계산한다."""
    ed = (state or {}).get("edition")
    if ed and ed["date"] == date:
        return copy.deepcopy((state or {}).get("base"))
    return copy.deepcopy(ed) if ed and ed["date"] < date else None


def next_state(state, snap):
    """이번 판의 기록 snap을 넣은 새 상태. 같은 날짜를 다시 돈 것이면 base를 그대로 두고, 새 날짜면 지난 판이 base가 된다."""
    return {"schema": SCHEMA, "edition": copy.deepcopy(snap), "base": state_base(state, snap["date"])}


def in_window(window, date, time=None):
    """일정이 수집 창과 맞는가. 시각(HH:MM, KST)이 있으면 from < 시각 ≤ to, 없으면 날짜가 창의 날짜들에 걸치면 맞다."""
    a, b = parse_iso(window["from"]), parse_iso(window["to"])
    day = datetime.date.fromisoformat(date)
    if time is None:
        return a.date() <= day <= b.date()
    h, m = map(int, time.split(":"))
    return a < _at(day, h, m) <= b


def rate_fits(series, asof, window):
    """금리의 자료일이 수집 창과 맞는가 — 그 자료일의 마감 시각(kr: 그날 16:00, us: 다음 날 07:00 KST)이 창 안에 있을 때만.
    안 맞으면 금리 변동 가산(M)은 0이고 head의 방향 칸을 비운다."""
    plus, h, m = TH["close_kst"][series]
    close = _at(datetime.date.fromisoformat(asof) + datetime.timedelta(days=plus), h, m)
    return parse_iso(window["from"]) < close <= parse_iso(window["to"])


# ---------- 주소 · id · 열쇠 · 제목 해시 ----------


def post_url(ch, post):
    """공개 주소는 채널 이름 + 정수 글 번호로만 조립한다(글에서 읽은 주소를 옮기지 않는다)."""
    if not (isinstance(ch, str) and HANDLE_RE.fullmatch(ch)) or type(post) is not int or not 0 < post <= MAX_POST:
        raise ValueError("채널 이름이나 글 번호가 꼴에 맞지 않음")
    return f"https://t.me/{ch}/{post}"


def item_id(date, ch, post):
    """항목 id — 순위가 아니라 묶음의 씨앗 글로 만든다: "20261008-yieldnspread-1234"."""
    _date(date, "date")
    post_url(ch, post)
    return f"{date.replace('-', '')}-{ch}-{post}"


def key_of(kind, material):
    """묶기 열쇠 "<종류>:<sha1 앞 12자리>". 재료(전달 원글 "채널/번호" · 정규화한 주소 · 카드 제목 · "낱말|지역" 등)는 해시로만 남는다."""
    if kind not in KEY_KINDS or not isinstance(material, str) or not material:
        raise ValueError("열쇠 종류나 재료가 맞지 않음")
    return f"{kind}:{hashlib.sha1(unicodedata.normalize('NFKC', material).encode('utf-8')).hexdigest()[:12]}"


def primary_key(keys):
    """묶음의 대표 열쇠 — 종류 우선순위(f → u → t → n → k → g), 그다음 글자순."""
    if not keys:
        raise ValueError("열쇠가 없음")
    return min(keys, key=lambda k: (KEY_KINDS.index(k[0]), k))


def title_sha(title):
    """채널 제목 해시(sha256 앞 16자리). 제목은 미리보기 쪽의 og:title — page_title()로 읽은 값."""
    return hashlib.sha256(R.norm_text(title).encode("utf-8")).hexdigest()[:16]


class _OgTitle(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("property") == "og:title" and self.title is None:
            self.title = a.get("content")

    handle_startendtag = handle_starttag


def page_title(page):
    """t.me/s 미리보기 HTML의 채널 제목(og:title). 없으면 None."""
    p = _OgTitle()
    p.feed(page)
    p.close()
    return R.norm_text(p.title) or None


# ---------- 여러 단계가 같이 쓰는 규칙 ----------


def seed_of(members):
    """묶음의 씨앗 글 — 가장 이른 원천(role source) 글, 원천이 없으면 가장 이른 글. → {"ch", "id"}"""
    pool = [m for m in members if m["role"] == "source"] or list(members)
    m = min(pool, key=lambda x: (x["at"], x["ch"], x["id"]))
    return {"ch": m["ch"], "id": m["id"]}


def pick_links(members, limit=None, personal_max=None):
    """묶음의 글들 → 공개 링크 [{"ch", "url", "at", "fwd"}]. 원천 채널만, 채널마다 한 글(전달이 아닌 글 먼저, 그다음 이른 글).
    순서는 전달 아닌 글 → 채권 → 애널 → 개인 → 이른 글. 개인 채널은 personal_max개까지, 모두 limit개까지."""
    limit = TH["links_max"] if limit is None else limit
    personal_max = TH["links_personal_max"] if personal_max is None else personal_max
    best = {}
    for m in members:
        rank = (m["fwd"], m["at"], m["id"])
        if m["role"] == "source" and (m["ch"] not in best or rank < best[m["ch"]][0]):
            best[m["ch"]] = (rank, m)
    out, personal = [], 0
    for _, m in sorted(best.values(), key=lambda b: (b[1]["fwd"], R.GROUP_ORDER.index(b[1]["group"]), b[1]["at"], b[1]["ch"])):
        if m["group"] == "personal":
            personal += 1
            if personal > personal_max:
                continue
        out.append({"ch": m["ch"], "url": post_url(m["ch"], m["id"]), "at": m["at"], "fwd": m["fwd"]})
    return out[:limit]


def coverage_verdict(channels):
    """채널별 읽기 건강 숫자(collect_status.channels) → 수집 판정. broken(본문 비율이 절반 아래 — 형식이 바뀐 것) > short(채권 3곳
    미만 또는 전체 16곳 미만) > ok. → {"verdict", "channels_ok", "channels_total", "bond_ok", "bond_total", "posts", "with_text"}"""
    ok = [c for c in channels if c["ok"]]
    out = {"channels_ok": len(ok), "channels_total": len(channels),
           "bond_ok": sum(c["group"] == "bond" for c in ok), "bond_total": sum(c["group"] == "bond" for c in channels),
           "posts": sum(c["posts"] for c in ok), "with_text": sum(c["with_text"] for c in ok)}
    if out["posts"] and out["with_text"] < TH["min_text_ratio"] * out["posts"]:
        return {"verdict": "broken", **out}
    short = out["bond_ok"] < TH["min_bond_ok"] or out["channels_ok"] < TH["min_total_ok"]
    return {"verdict": "short" if short else "ok", **out}


# ---------- 닫힌 글자 검사 ----------


def is_closed(s, handles=(), labels=()):
    """문자열 하나가 허용 목록(사전 낱말·결과 낱말·코드·고정 문구·숫자+단위·시각·날짜·열쇠·해시·목록 채널의 이름·주소·id)인가."""
    if s in WORDS or s in handles or s in labels or R.is_num(s) or R.is_phrase(s):
        return True
    if any(rx.fullmatch(s) for rx in (ISO_RE, DATE_RE, HHMM_RE, KEY_RE, SHA_RE)):
        return True
    m = URL_RE.fullmatch(s) or ID_RE.fullmatch(s)
    return bool(m) and m.group("ch") in handles


def closed_violations(obj, handles=(), labels=(), path="$"):
    """공개 자료에서 허용 목록으로 다시 조립되지 않는 문자열·칸 이름의 자리를 돌려준다(값은 돌려주지 않는다). 비어 있어야 통과.
    handles = 목록의 채널 이름(handles_of), labels = 출처 라벨(sources.json을 볼 때만 준다)."""
    if isinstance(obj, str):
        return [] if is_closed(obj, handles, labels) else [path]
    if isinstance(obj, list):
        return [p for i, x in enumerate(obj) for p in closed_violations(x, handles, labels, f"{path}[{i}]")]
    if isinstance(obj, dict):
        out = []
        for k, x in obj.items():
            known = isinstance(k, str) and (k in FIELDS or k in handles)
            out += closed_violations(x, handles, labels, f"{path}.{k}") if known else [f"{path}.<정해지지 않은 칸>"]
        return out
    return [] if obj is None or type(obj) in (bool, int, float) else [path]


# ---------- 읽고 쓰기 · 실행 감싸기 ----------


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def read_json(path, default=...):
    """JSON 파일을 읽는다. 파일이 없으면 default(주지 않았으면 FileNotFoundError), 깨졌으면 ValueError(내용은 싣지 않는다)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if default is ...:
            raise
        return copy.deepcopy(default)
    except ValueError:
        raise ValueError("JSON을 읽을 수 없음") from None


def write_json(path, obj):
    """임시 파일에 쓰고 바꿔치기한다(중간에 죽어도 반쯤 쓴 파일이 남지 않게)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dump(obj))
    os.replace(tmp, path)


def report(name, **facts):
    """공개 Actions 로그에 남길 한 줄 "[이름] 칸=값 …". 값은 숫자·참거짓·닫힌 낱말(날짜·시각·코드)만 — 그 밖의 글자는 가린다."""
    def show(v):
        return str(v) if type(v) in (int, float, bool) or (isinstance(v, str) and is_closed(v)) else "(가림)"
    print(f"[{name}] " + " ".join(f"{k}={show(v)}" for k, v in facts.items()))


def run_cli(name, main, argv=None):
    """main(argv)를 돌려 종료코드를 낸다. 예외가 나면 예외 종류 이름만 찍는다 — 추적문과 메시지에 채널 글 조각이 섞여
    공개 로그로 나가지 않게. 스크립트 끝은 sys.exit(run_cli("tg_collect", main)) 한 줄이다."""
    try:
        code = main(argv)
        return 0 if code is None else code
    except SystemExit as e:                        # argparse의 사용법 오류
        return e.code if type(e.code) is int else 1
    except BaseException as e:
        print(f"[{name}] 실패: {type(e).__name__}", file=sys.stderr)
        return 1
