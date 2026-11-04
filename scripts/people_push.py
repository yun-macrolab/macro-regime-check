#!/usr/bin/env python3
"""연준 인물 새 발언 게시 — 게시 전용 폴더에서 data/people_remarks.json 하나만 main에 올린다 (2026-11-04, PC에서만 돈다).

비공개 파이프라인의 결론 런이 사용자 폴더 .macro-notes/people-remarks.json(자동 분류한 발언 — 기준선 대비)을 쓰고, 저녁판 예약 작업
(scripts/evening/Evening-Summary.ps1)이 저녁판 앞에 따로 이것을 부른다(2026-11-04 검토 push-3 — 이 sync가 끊긴 앞 실행의 잔재를 두 게시기
몫 모두 되돌리므로, 먼저 돌면 저녁판의 picks_push.sync가 dirty로 막히지 않는다). 저녁판의 종료코드 · 스위치(EVENING_ENABLED)와 무관하다.
그 예약 작업을 지우면(-Unschedule) 이 게시도 — 내리기(agree=N)까지 — 멈춘다. 저녁판만 멈추려면 스위치를 끄고 작업은 둔다.
여기에는 모델 호출도 바깥 요청도 없다 — git · gh와, 받은 파일을 믿지 않고 다시 보는 검사뿐이다. 사람 확인 없이 매일 올라간다
(2026-11-04 사용자 결정). 사람이 내린 발언(평가 로그 agree=N)은 비공개 쪽이 내보내지 않는다 — 다음 결론 런 → 다음 게시에서 빠진다.

  sync      작업 폴더를 origin/main의 끝으로: 이 스크립트가 남긴 발언 파일(고쳐짐 · 새 파일 · 스테이징만 됨)을 먼저 되돌리고 → 나머지는
            저녁판의 picks_push.sync(저녁판 잔재를 되돌리고 fetch → checkout --detach origin/main). 두 파일 말고 바뀐 것이 있으면
            아무것도 건드리지 않고 Stop("dirty").
  load      원본(--source)을 읽어 약속(꼴 · 열거값 · 길이 · id 규칙 · 날짜 · 명단 · 개수 · 크기)대로 검사한다 → 공개 꼴(generated_at 대신
            asof = 그 날짜)로 바꾼다. 명단은 그 폴더의 site/people-data.js의 key. 하나라도 어긋나면 Stop("file") — 아무것도 올리지 않는다.
  publish   올라가 있는 파일과 remarks · held가 같으면 "same"(asof만 다를 때 커밋 없음) → 파일을 쓰고 → 바뀐 것이 그 한 줄뿐인가 →
            다시 읽어 검사(다시 쓴 바이트와 같은가) → 공개 전 검사(scripts/check_blind.py) → 작업 폴더가 origin/main의 끝인가 →
            커밋('data: YYYY-MM-DD 연준 인물 발언') → 커밋 1개 · 파일 1개인가 → push(gh 로그인을 빌린다).
            push가 거절됐고 그사이 main이 움직였으면 한 번만 다시: 새 main의 명단으로 다시 보고(맞지 않으면 Stop("moved")) 같은 바이트를
            새 main 위에 커밋한다. push하면 daily.yml(push 실행)이 검사하고 배포한다.
  정리      sync 뒤에 멈추면(어떤 사유든, 예상하지 못한 예외도) 발언 파일의 스테이징을 풀고 파일을 되돌린다(새 파일이면 지운다) —
            저녁판 게시(picks_push.sync)가 다음 실행에서 dirty로 막히지 않게.
멈추는 사유는 Stop(코드)로만 알린다 — 메시지 · 로그에 경로 · 출력 · 파일의 글자를 싣지 않는다:
  source 원본 파일이 없다 · file 원본이 약속에 어긋난다(로그의 why에 어긋난 규칙 이름) · roster 명단(site/people-data.js)을 읽지 못했다 ·
  dirty · status · fetch · detach · git(sync) · scope 올릴 것에 다른 파일이 섞였다 · blind 공개 전 검사에 걸렸거나 검사할 수 없다 ·
  head 작업 폴더가 origin/main의 끝이 아니다 · commit · commits 커밋이 1개가 아니거나 다른 파일이 들었다 ·
  moved 다시 올리려는 사이 새 main의 명단에 맞지 않게 됐다 · push

사용법:  python -X utf8 scripts/people_push.py --repo-dir <게시 전용 폴더> --source <원본 json> [--dry-run] [--log 파일]
  --dry-run  git을 부르지 않는다 — 검사하고 <repo>/.work/people_dry/people_remarks.json에 공개 꼴을 쓴다(로그도 그 폴더에).
종료코드: 0 올렸거나(pushed) 같다(same) / 2 올리지 않았다(Stop) / 1 예상하지 못한 실패
로그: 한 실행에 한 줄, 사용자 폴더의 .macro-notes/people-push.log — 코드 · 개수 · 날짜뿐이다(파일의 글은 싣지 않는다).
약속(두 저장소가 같아야 한다): 아래 상수들 — 비공개 쪽의 짝 테스트가 견준다.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "people_push"

# ── 약속(비공개 fed_people의 내보내기와 같은 값) ─────────────────────────────────────
SCHEMA = "people-remarks/1"
SOURCE_KEYS = ("schema", "generated_at", "window_from", "remarks", "held")     # 비공개가 쓰는 꼴
PUBLIC_KEYS = ("schema", "asof", "window_from", "remarks", "held")             # 공개 꼴(generated_at 대신 그 날짜)
FIELDS = ("id", "who", "said_on", "venue", "access", "topic", "quote", "vs_base", "basis", "why", "conditional", "dissent",
          "source", "title", "tags", "baseline_asof", "baseline_review")
BASIS_KEYS = ("path", "text")
VENUES = ("기자회견", "연설", "인터뷰", "의회 증언", "투표", "의사록", "기고", "기타")
ACCESS = ("직접", "전언")
VS_BASE = ("평소와 같음", "평소보다 매파", "평소보다 비둘기", "새 주제")
SIDES = ("인상", "인하", "동결", "문구")                     # 반대표 — venue=투표일 때만
TAGS = ("블랙아웃 중 — 전언 확인", "기준선 초안")
REVIEWS = ("draft", "approved")
LIMITS = {"topic": 40, "why": 120, "conditional": 80, "source": 40, "title": 80}   # 글자 수 상한("" 가능)
QUOTE_WORDS = 15                                            # 넘으면 비공개 쪽이 잘라 16번째 토막에 CUT
CUT = "…"
BASIS_MAX, BASIS_TEXT, PATH_MAX = 4, 120, 80                # 견준 항목 1~4개 · 글 120자 · 프로필 경로 80자
PER_PERSON = 30                                             # 한 사람 최신 30개
MAX_ITEMS = 400
MAX_BYTES = 256 * 1024                                      # 파일 크기(UTF-8)
WINDOW_DAYS = 365                                           # window_from = 쓴 날 − 365일
AHEAD_DAYS = 1                                              # 날짜는 실행일 + 1일까지(시간대 차)
ID_LEN = 12
INVISIBLE = ("Cc", "Cf", "Zl", "Zp", "Cs")                  # 제어 · 서식(폭 없는 글자) · 줄/문단 구분 · 서로게이트 — check_blind와 같은 묶음
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", re.ASCII)
ID_RE = re.compile(r"[0-9a-f]{12}", re.ASCII)
PATH_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d{1,4}\])*(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\d{1,4}\])*)*", re.ASCII)
KEY_RE = re.compile(r"[a-z]+", re.ASCII)

# ── 게시 ────────────────────────────────────────────────────────────────────────────
PATH = "data/people_remarks.json"
ROSTER = "site/people-data.js"
MESSAGE = "data: {date} 연준 인물 발언"
# 인증은 gh 로그인을 빌린다 — 앞의 빈 값이 다른 credential helper(저장된 열쇠)를 지운다(picks_push와 같다)
PUSH = ("-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential", "push", "origin", "HEAD:main")
STATUS = ("-c", "core.quotePath=false", "status", "--porcelain", "--untracked-files=all")
CHANGED = (f" M {PATH}", f"?? {PATH}")                     # 고쳐진 파일 · 처음 생긴 파일 — 올릴 수 있는 변경은 이 한 줄뿐이다
STAGED = tuple(f"{xy} {PATH}" for xy in ("A ", "M ", "AM", "MM"))     # 커밋 직전에 끊긴 실행의 잔재 — sync가 푼다
UNSTAGE = ("reset", "--quiet", "--", PATH)
GIT_S, CHECK_S = 120, 600                                   # 명령 하나의 시간 제한(초)
WORD_RE = re.compile(r"[a-z_]{1,20}", re.ASCII)            # 로그 값의 꼴 — 코드 · 사유 이름
KIND_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,60}", re.ASCII)


class Stop(Exception):
    """게시를 멈춘 사유 — 코드만 들고 다닌다. why = 검사에 걸린 규칙 이름(로그용, 파일의 글이 아니다)."""

    def __init__(self, code, why=None):
        super().__init__(code)
        self.code, self.why = code, why


class Bad(ValueError):
    """원본이 약속에 어긋난다 — 어긋난 규칙 이름만 든다."""

    def __init__(self, why):
        super().__init__(why)
        self.why = why


def remark_id(who, said_on, venue):
    """발언 id = sha1("who|said_on|venue")의 앞 12자(소문자 16진). 비공개 쪽과 같은 규칙."""
    return hashlib.sha1(f"{who}|{said_on}|{venue}".encode("utf-8")).hexdigest()[:ID_LEN]


def dump(doc):
    """공개 파일의 바이트 꼴 — 한 줄 JSON(저녁판 파일과 같다). 다시 쓴 바이트와 견줘 다른 것이 섞이지 않았는지 본다."""
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# ---------- 검사 ----------

def _day(v, why):
    if type(v) is not str or not DATE_RE.fullmatch(v):
        raise Bad(why)
    try:
        return datetime.date.fromisoformat(v)
    except ValueError:
        raise Bad(why) from None


def _text(v, why, limit=None, empty=True):
    """글 칸: 문자열 · 앞뒤 공백 없음 · 보이지 않는 글자 없음 · 주소("://") 없음 · 글자 수 상한."""
    if type(v) is not str or (not v and not empty):
        raise Bad(why)
    if v != v.strip() or "://" in v or any(unicodedata.category(c) in INVISIBLE for c in v):
        raise Bad("text")
    if limit is not None and len(v) > limit:
        raise Bad(why)
    return v


def _quote_ok(q):
    words = q.split()
    return len(words) <= QUOTE_WORDS or (len(words) == QUOTE_WORDS + 1 and words[-1] == CUT)


def _remark(r, keys, lo, hi, today):
    """발언 하나 → 같은 꼴의 새 dict(칸 차례는 FIELDS). 어긋나면 Bad(규칙 이름)."""
    if type(r) is not dict or set(r) != set(FIELDS):
        raise Bad("fields")
    who = _text(r["who"], "who", empty=False)
    if not KEY_RE.fullmatch(who) or who not in keys:
        raise Bad("who")
    said = _day(r["said_on"], "said_on")
    if not lo <= said <= hi:
        raise Bad("said_on")
    for k, allowed in (("venue", VENUES), ("access", ACCESS), ("vs_base", VS_BASE), ("baseline_review", REVIEWS)):
        if type(r[k]) is not str or r[k] not in allowed:
            raise Bad(k)
    if type(r["id"]) is not str or not ID_RE.fullmatch(r["id"]) or r["id"] != remark_id(who, r["said_on"], r["venue"]):
        raise Bad("id")
    for k, n in LIMITS.items():
        _text(r[k], k, n)
    q = _text(r["quote"], "quote")
    if q and not _quote_ok(q):
        raise Bad("quote")
    d = _text(r["dissent"], "dissent")
    if d and (d not in SIDES or r["venue"] != "투표"):
        raise Bad("dissent")
    basis = r["basis"]
    if type(basis) is not list or not 1 <= len(basis) <= BASIS_MAX:
        raise Bad("basis")
    for b in basis:
        if type(b) is not dict or set(b) != set(BASIS_KEYS):
            raise Bad("basis")
        p = _text(b["path"], "basis", PATH_MAX, empty=False)
        if not PATH_RE.fullmatch(p):
            raise Bad("basis")
        _text(b["text"], "basis", BASIS_TEXT, empty=False)
    tags = r["tags"]
    if type(tags) is not list or len(set(map(str, tags))) != len(tags) or any(type(t) is not str or t not in TAGS for t in tags):
        raise Bad("tags")
    if _day(r["baseline_asof"], "baseline_asof") > today + datetime.timedelta(days=AHEAD_DAYS):
        raise Bad("baseline_asof")
    out = {k: r[k] for k in FIELDS}
    out["basis"] = [{"path": b["path"], "text": b["text"]} for b in basis]
    out["tags"] = list(tags)
    return out


def _order(remarks):
    """최신순(said_on 내림, 같으면 who, venue 올림)."""
    return sorted(sorted(remarks, key=lambda r: (r["who"], r["venue"])), key=lambda r: r["said_on"], reverse=True)


def _body(doc, keys, today, asof):
    """remarks · held · window_from 검사(두 꼴 공통) → (발언 목록(최신순), held)."""
    hi = _day(asof, "asof")
    if hi > today + datetime.timedelta(days=AHEAD_DAYS):
        raise Bad("asof")
    lo = _day(doc["window_from"], "window_from")
    if lo > hi or (hi - lo).days > WINDOW_DAYS + 1:            # 하루 여유 — 비공개 쪽 '오늘'이 자정을 넘긴 날
        raise Bad("window_from")
    held = doc["held"]
    if type(held) is not int or held < 0:
        raise Bad("held")
    remarks = doc["remarks"]
    if type(remarks) is not list or len(remarks) > MAX_ITEMS:
        raise Bad("count")
    out = [_remark(r, keys, lo, hi, today) for r in remarks]
    seen, per = set(), {}
    for r in out:
        k = (r["who"], r["said_on"], r["venue"])
        if k in seen:
            raise Bad("duplicate")
        seen.add(k)
        per[r["who"]] = per.get(r["who"], 0) + 1
        if per[r["who"]] > PER_PERSON:
            raise Bad("per_person")
    return _order(out), held


def check_source(raw, keys, today):
    """비공개가 쓴 원본(바이트) → 공개 꼴 dict. 어긋나면 Bad(규칙 이름) — 메시지에 파일의 글자를 싣지 않는다."""
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise Bad("size")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Bad("json") from None
    if type(doc) is not dict or set(doc) != set(SOURCE_KEYS) or doc["schema"] != SCHEMA:
        raise Bad("schema")
    stamp = doc["generated_at"]
    if type(stamp) is not str or not STAMP_RE.fullmatch(stamp):
        raise Bad("generated_at")
    try:
        if datetime.datetime.fromisoformat(stamp).tzinfo is None:
            raise Bad("generated_at")
    except ValueError:
        raise Bad("generated_at") from None
    remarks, held = _body(doc, keys, today, stamp[:10])
    public = {"schema": SCHEMA, "asof": stamp[:10], "window_from": doc["window_from"], "remarks": remarks, "held": held}
    if len(dump(public)) > MAX_BYTES:
        raise Bad("size")
    return public


def check_public(raw, keys, today):
    """공개 파일(바이트 — data/people_remarks.json) → dict. 꼴 · 검사가 원본과 같고, 바이트가 dump(그 자료)와 같아야 한다."""
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise Bad("size")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Bad("json") from None
    if type(doc) is not dict or list(doc) != list(PUBLIC_KEYS) or doc["schema"] != SCHEMA:
        raise Bad("schema")
    remarks, held = _body(doc, keys, today, doc["asof"])
    if remarks != doc["remarks"] or held != doc["held"] or dump(doc) != raw:
        raise Bad("bytes")                                     # 차례 · 칸 차례 · 바이트 꼴까지 게시기가 쓴 그대로
    return doc


def roster(repo):
    """그 폴더의 site/people-data.js → 사람 key 집합. 읽지 못하면 Stop("roster")."""
    try:
        with open(os.path.join(repo, *ROSTER.split("/")), encoding="utf-8") as f:
            text = f.read()
        m = re.fullmatch(r"\s*(?:/\*(?:(?!\*/).)*\*/\s*)?window\.PEOPLE_DATA = (\{.*\});\s*", text, re.S)
        people = json.loads(m.group(1))["people"] if m else None
        keys = {p["key"] for p in people} if type(people) is list and all(type(p) is dict for p in people) else set()
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        keys = set()
    if not keys or not all(type(k) is str and KEY_RE.fullmatch(k) for k in keys):
        raise Stop("roster")
    return keys


def load(source, keys, today):
    """원본 파일을 읽어 검사한다 → 공개 꼴. 파일이 없으면 Stop("source"), 어긋나면 Stop("file", 규칙 이름)."""
    try:
        with open(source, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
    except FileNotFoundError:
        raise Stop("source") from None
    except OSError:
        raise Stop("source", "read") from None
    try:
        return check_source(raw, keys, today)
    except Bad as e:
        raise Stop("file", e.why) from None


def counts(doc):
    """로그에 남길 개수."""
    rs = doc["remarks"] if doc else []
    return {"remarks": len(rs), "held": doc["held"] if doc else 0, "people": len({r["who"] for r in rs})}


# ---------- git ----------

def _call(run, cmd, repo, limit):
    """명령 하나 → (종료코드, 출력). 실행 자체가 안 되면(없는 프로그램 · 시간 초과) (None, "")."""
    try:
        r = run(list(cmd), cwd=repo, capture_output=True, timeout=limit)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace")


def _git(run, repo, code, *args):
    rc, out = _call(run, ("git", *args), repo, GIT_S)
    if rc is None:
        raise Stop("git")
    if rc != 0:
        raise Stop(code)
    return out


def _lines(run, repo):
    return [x for x in _git(run, repo, "status", *STATUS).split("\n") if x]


def _file(repo):
    return os.path.join(repo, *PATH.split("/"))


def _undo(run, repo, line):
    """발언 파일의 변경을 되돌린다 — 고쳐진 것이면 HEAD의 것으로, 처음 생긴 것이면 지운다."""
    if line.startswith("??"):
        os.remove(_file(repo))
    else:
        _git(run, repo, "status", "checkout", "--quiet", "--", PATH)


def _picks():
    """저녁판 게시기(scripts/evening/picks_push.py) — 부를 때만 싣는다(이 모듈의 상수만 보는 짝 테스트가 저녁판 코드를 싣지 않게)."""
    folder = os.path.join(HERE, "evening")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import picks_push
    return picks_push


def sync(repo, run=subprocess.run):
    """작업 폴더를 origin/main의 끝으로. 발언 파일 · 저녁판 파일 말고 바뀐 것이 있으면 Stop("dirty") — 아무것도 건드리지 않는다."""
    pp = _picks()
    lines = _lines(run, repo)
    if any(x not in CHANGED + STAGED + pp.CHANGED + pp.STAGED for x in lines):
        raise Stop("dirty")
    if any(x in STAGED for x in lines):                       # 커밋 직전에 끊긴 실행의 잔재 — 그 한 경로의 스테이징만 푼다
        _git(run, repo, "status", *UNSTAGE)
        lines = _lines(run, repo)
        if any(x not in CHANGED + pp.CHANGED + pp.STAGED for x in lines):
            raise Stop("dirty")
    for x in lines:
        if x in CHANGED:
            _undo(run, repo, x)
    try:
        pp.sync(repo, run)                                    # 저녁판 잔재 · fetch · checkout --detach origin/main
    except pp.Stop as e:
        raise Stop(e.code) from None


def tidy(repo, run=subprocess.run):
    """멈춘 뒤 정리 — 발언 파일의 스테이징을 풀고 되돌린다(새 파일이면 지운다). 예외를 내지 않는다. 다른 파일은 건드리지 않는다."""
    try:
        _call(run, ("git", *UNSTAGE), repo, GIT_S)
        rc, out = _call(run, ("git", *STATUS), repo, GIT_S)
        for x in (out.split("\n") if rc == 0 else []):
            if x in CHANGED:
                _undo(run, repo, x)
    except (Stop, OSError):
        pass


def _published(repo):
    """지금 폴더(= main의 끝)에 올라 있는 공개 파일 → dict 또는 None(없거나 읽을 수 없음)."""
    try:
        with open(_file(repo), "rb") as f:
            doc = json.loads(f.read(MAX_BYTES + 1).decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        return None
    return doc if type(doc) is dict else None


def _same(repo, doc):
    old = _published(repo)
    return old is not None and old.get("remarks") == doc["remarks"] and old.get("held") == doc["held"]


def _write(repo, raw):
    """임시 파일(.work/ — git 제외)에 쓰고 바꿔치기한다. 죽어도 data/에 반쯤 쓴 파일이나 .tmp가 남지 않는다."""
    tmp_dir = os.path.join(repo, ".work", "people_push")
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(_file(repo)), exist_ok=True)
    tmp = os.path.join(tmp_dir, "people_remarks.json.tmp")
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, _file(repo))


def _only_ours(run, repo):
    """바뀐 것이 발언 파일 한 줄뿐인가 → 그 줄(바뀐 것이 없으면 None). 다른 것이 섞였으면 Stop("scope")."""
    lines = _lines(run, repo)
    if not lines:
        return None
    if len(lines) != 1 or lines[0] not in CHANGED:
        raise Stop("scope")
    return lines[0]


def _checked(repo, raw, keys, today):
    """쓴 파일을 다시 읽어 검사한다 — 바이트가 쓰려던 것과 같고 공개 꼴 검사를 지나는가."""
    try:
        with open(_file(repo), "rb") as f:
            got = f.read(MAX_BYTES + 1)
        check_public(got, keys, today)
    except (OSError, Bad):
        raise Stop("file", "written") from None
    if got != raw:
        raise Stop("file", "written")


def _commit(run, repo, date):
    """발언 파일만 커밋하고, 올릴 것이 그 커밋 하나 · 그 파일 하나인지 다시 본다. 커밋하지 못했으면 스테이징을 풀고 멈춘다."""
    try:
        _git(run, repo, "commit", "add", "--", PATH)
        _git(run, repo, "commit", "commit", "--quiet", "-m", MESSAGE.format(date=date), "--", PATH)
    except Stop:
        _call(run, ("git", *UNSTAGE), repo, GIT_S)
        raise
    count = _git(run, repo, "commits", "rev-list", "--count", "origin/main..HEAD").strip()
    names = _git(run, repo, "commits", "-c", "core.quotePath=false", "diff", "--name-only", "origin/main", "HEAD").split("\n")
    if count != "1" or [n for n in names if n] != [PATH]:
        raise Stop("commits")


def _push(run, repo):
    rc, _ = _call(run, ("git", *PUSH), repo, GIT_S)
    return rc == 0


def publish(repo, doc, keys, today, run=subprocess.run, python=sys.executable):
    """검사를 지난 공개 꼴 doc을 main에 올린다 → "pushed" · "same". 올리지 않고 멈출 때는 Stop(코드). sync 뒤에만 부른다."""
    if _same(repo, doc):
        return "same"
    raw = dump(doc)
    _write(repo, raw)
    line = _only_ours(run, repo)
    if line is None:
        return "same"                                          # 바이트까지 같다(asof도 같은 날)
    _checked(repo, raw, keys, today)
    rc, _ = _call(run, (python, "-X", "utf8", os.path.join("scripts", "check_blind.py")), repo, CHECK_S)
    if rc != 0:                                                # 걸렸거나(1) 검사할 수 없거나(2 — 검사어 없음 등). 어느 쪽도 통과가 아니다
        raise Stop("blind")
    here = _git(run, repo, "commits", "rev-parse", "HEAD", "origin/main").split()
    if len(here) != 2 or here[0] != here[1]:                  # 가지 위나 올리지 않은 커밋 위 — 거기에 커밋을 남기지 않는다
        raise Stop("head")
    base = here[1]
    _commit(run, repo, doc["asof"])
    if _push(run, repo):
        return "pushed"
    _git(run, repo, "fetch", "fetch", "--quiet", "origin", "main")
    if _git(run, repo, "commits", "rev-parse", "origin/main").strip() == base:
        raise Stop("push")                                     # main은 그대로인데 거절됐다(인증 · 훅 · 네트워크) — 다시 해도 같다
    _git(run, repo, "detach", "checkout", "--quiet", "--detach", "origin/main")       # 방금 커밋은 두고 새 main의 끝으로
    try:
        new_keys = roster(repo)
        check_public(raw, new_keys, today)                     # 새 main의 명단으로 다시 — 그사이 빠진 사람이 있으면 올리지 않는다
    except (Stop, Bad):
        raise Stop("moved") from None
    if _same(repo, doc):
        return "same"
    _write(repo, raw)
    if _only_ours(run, repo) is None:
        return "same"
    _commit(run, repo, doc["asof"])
    if _push(run, repo):
        return "pushed"
    raise Stop("push")


# ---------- 한 번에 돌리기 ----------

def note(log, at, **facts):
    """로그 한 줄(표준 출력에도) — 코드 · 개수 · 날짜뿐이다. 정해 둔 꼴이 아닌 값은 가린다(파일의 글이 실수로라도 실리지 않게)."""
    def show(k, v):
        if type(v) in (int, bool):
            return str(v).lower()
        ok = isinstance(v, str) and (DATE_RE.fullmatch(v) or (KIND_RE if k == "kind" else WORD_RE).fullmatch(v))
        return v if ok else "(hidden)"
    line = f"{at} [{NAME}] run " + " ".join(f"{k}={show(k, v)}" for k, v in facts.items())
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
    except OSError:
        pass                                                   # 로그를 못 써도 결과는 그대로다


def log_path(a):
    if a.log:
        return os.path.abspath(a.log)
    if a.dry_run:
        return os.path.join(os.path.abspath(a.repo_dir), ".work", "people_dry", "people-push.log")
    return os.path.join(os.path.expanduser("~"), ".macro-notes", "people-push.log")


def dry_out(repo):
    return os.path.join(os.path.abspath(repo), ".work", "people_dry", "people_remarks.json")


def run_all(a, run=subprocess.run, python=sys.executable, today=None):
    """sync → 원본 검사 → 공개 꼴 → 올리기 → (결과, 자료). Stop은 그대로 올린다 — sync 뒤에 멈추면 발언 파일을 정리한 뒤에."""
    repo = os.path.abspath(a.repo_dir)
    today = today or datetime.date.today()
    if a.dry_run:                                              # git 없이 — 검사하고 작업 폴더의 .work/에만 쓴다
        doc = load(a.source, roster(repo), today)
        out = dry_out(repo)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(dump(doc))
        return "dry", doc
    sync(repo, run)
    try:
        keys = roster(repo)                                    # 방금 옮긴 main의 명단
        doc = load(a.source, keys, today)
        return publish(repo, doc, keys, today, run, python), doc
    except BaseException:
        tidy(repo, run)                                        # 저녁판 게시가 다음 실행에서 dirty로 막히지 않게
        raise


def parse(argv=None):
    ap = argparse.ArgumentParser(description="연준 인물 새 발언(자동 분류) — data/people_remarks.json 하나만 main에 올린다(이 PC에서만)")
    ap.add_argument("--repo-dir", required=True, help="게시 전용 저장소 작업 폴더")
    ap.add_argument("--source", required=True, help="비공개 파이프라인이 쓴 원본(사용자 폴더의 .macro-notes/people-remarks.json)")
    ap.add_argument("--dry-run", action="store_true", help="git을 부르지 않고 검사해 <repo>/.work/people_dry/에 쓴다")
    ap.add_argument("--log", default=None, help="로그 파일(기본: 사용자 폴더의 .macro-notes/people-push.log)")
    return ap.parse_args(argv)


def main(argv=None, run=subprocess.run, python=sys.executable, today=None, now=None):
    a = parse(argv)
    at = (now() if now else datetime.datetime.now().astimezone()).replace(microsecond=0).isoformat()     # 이 PC의 시각(오프셋 포함)
    log = log_path(a)
    try:
        result, doc = run_all(a, run, python, today)
    except Stop as e:
        note(log, at, code=e.code, **({"why": e.why} if e.why else {}))
        return 2
    except Exception as e:                                     # 예상하지 못한 실패 — 종류 이름만 남긴다
        note(log, at, code="error", kind=type(e).__name__)
        return 1
    if a.dry_run:
        print(dry_out(a.repo_dir), flush=True)
    note(log, at, code="ok", result=result, asof=doc["asof"], **counts(doc))
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):                   # 한국어 Windows 콘솔에서도 깨지지 않게
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:
        print(f"[{NAME}] 실패: {type(e).__name__}", file=sys.stderr)
        sys.exit(1)
