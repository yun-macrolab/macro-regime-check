#!/usr/bin/env python3
"""저녁판 검사 — 공개 폴더의 JSON을 내보내도 되는지 본다 (2026-10-08, 1단계 규칙 선별판).

수집 잡에서 조립 직후 한 번(--raw: 원문과도 대조), 게시 잡에서 원문 없이 한 번 더 돈다. 읽기만 하고 아무것도 쓰지 않는다.
가장 중요한 검사는 닫힌 글자다: 공개 JSON의 모든 문자열과 칸 이름이 사전 낱말 · 출처 목록의 채널 이름 · 고정 문구 ·
숫자+허용 단위 · 시각 · https://t.me/<목록의 채널>/<글 번호>로 다시 조립돼야 한다(S.closed_violations). 원문 없이도 돈다.
'원문과 8자 이상 겹치지 않는다'는 검사는 두지 않는다 — 8자짜리 사전 낱말에 스스로 걸리고, 닫힌 글자가 더 강한 조건이다(설계 12절).

무엇이 걸리면 어떻게 되나 (설계 8절 — 위반마다 scope를 붙인다)
  link     허용되지 않은 주소(url) · 원천이 아닌 채널의 링크(role) · --raw: 수집되지 않은 글(unseen)        → 그 링크만 뺀다
  row      속보형·개인 단독 줄과 참고 줄의 같은 문제 · 닫히지 않은 글자(open) · --raw: 그 글에 없는 낱말·숫자(mismatch) → 그 줄만 뺀다
  item     항목 안의 닫히지 않은 글자(open, --raw로 원문과 8자 이상 겹치면 leak) · 링크가 남지 않은 항목(empty)   → 그 항목만 뺀다
  rate     금리가 0~20 밖 · 자료일이나 방향 칸이 수집 창과 맞지 않음(rate)                                 → 그 금리 칸을 비운다
  edition  형식(shape) · 크기(size) · 다시 쓴 바이트와 다름(canon) · 못 읽음(json) · 없는 파일(missing) · 계약에 없는 파일(stray) ·
           파일끼리 어긋남(cross) · 수집 판정이 숫자와 다름(coverage) · 0건 연속 셈이 다름(streak) · 뺀 뒤에도 남는 위반   → 판 중단(직전 판 유지)
빼는 일은 조립(digest_build)이 쓰기 전에 keep_items · keep_side · keep_context · head_line으로 한다. 그래서 쓰인 파일에서
위반이 하나라도 나오면 scope가 무엇이든 종료코드 1이다 — scope는 '무엇을 빼면 됐는가'를 로그로 알려 줄 뿐이다.

다시 셈해서 맞춰 보는 것 (조립과 같은 함수를 쓴다)
  head_line    금리 칸의 fits(자료일의 마감이 창 안)와 방향·커브·종가 기준 — 공개된 숫자와 창만으로 다시 나온다
  수집 판정    상태 파일의 채널별 숫자 + 출처 목록의 그룹 → S.coverage_verdict. 수집 부족이면 판이 short이고 꼭 볼 것이 비어야 한다
  next_streak  꼭 볼 것 0건이 이어진 판 수. 3판째(TH empty_streak_fail)면 상태의 사유가 empty_streak여야 한다
               (채권 채널의 새 글이 하나도 없던 날, 수집 부족·내린 판은 세지 않는다)

출력은 공개 Actions 로그에 남는다 — 파일 이름 · 위반 코드 · 자리(칸 이름과 번호)만 찍고 값은 찍지 않는다.
--strict: 폴더에 저녁판 파일(PUBLIC_FILES와 digest/<날짜>.json) 말고 아무것도 없어야 한다 — 이름이 digest로 시작하지 않는 파일 · 다른
하위 폴더 · 숨김 파일도 stray. 아티팩트로 올라가는 폴더(수집 잡의 <out>, 게시 잡이 받은 것)를 볼 때 쓴다. data/를 볼 때는 쓰지 않는다.
사용법: python scripts/evening/digest_check.py --public <폴더> [--raw .work/evening] [--sources data/sources.json] [--strict] [--alert]
종료코드: 0 통과 / 1 위반 / (--alert일 때만) 2 위반은 없지만 실행을 실패로 끝낼 상태(수집 부족 · 0건 연속 · 형식 바뀜 · 실행 실패)
"""
import argparse
import json
import os
import re
import sys

import digest_rules as R
import digest_schema as S

TH = S.TH
EDITION_BYTES = 20_000                  # 판 하나(digest.json)의 크기 상한 — 조립이 나머지 표를 줄여 맞춘다. 계약의 상한(TH bytes_max)보다 좁다
SERIES = {"kr10": "kr", "kr3": "kr", "us10": "us"}
SOURCE = tuple((g, "source") for g in R.GROUPS)                    # 항목의 링크로 나갈 수 있는 채널
SIDES = {"wire": tuple((g, "wire") for g in R.GROUPS), "solo": (("personal", "source"),)}
CONTEXT = tuple((g, "context") for g in R.GROUPS)
ALERT_REASONS = ("short", "empty_streak", "broken", "error")       # 판은 맞아도 실행을 실패로 끝낼 사유
CHAN_KEYS = ("ch", "ok", "code", "posts", "with_text", "in_window", "fail_streak")
COUNT_KEYS = ("channels_ok", "channels_total", "bond_ok", "bond_total", "posts", "with_text")
DAY_FILE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$", re.ASCII)
ROOTS = {"digest", "index", "state", "status", "sources", "calendar", "overrides"}     # 검증 메시지의 자리가 시작하는 이름
UNKNOWN = "<정해지지 않은 칸>"
STRAY = "(계약에 없는 이름)"
GRAM = 8                                # --raw: 닫히지 않은 글자가 원문과 이만큼 겹치면 '새어 나온 글자'(leak)로 부른다
MAX_LINES = 40
_STEP = re.compile(r"\.([^.\[]+)|\[(\d+)\]")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _f(file, at, code, scope="edition"):
    return {"file": file, "at": at, "code": code, "scope": scope}


def roles_of(sources):
    """sources.json → {채널 이름: (그룹, 역할)} — 제외(off) 채널도 들어 있다."""
    return {c["handle"]: (c["group"], c["role"]) for c in sources["channels"]}


def member_ok(m, roles):
    """묶음의 글이 지금의 출처 목록과 맞는가 — 채널이 목록에 있고 그룹·역할이 같다(조립이 링크·줄을 고르기 전에 본다)."""
    return roles.get(m["ch"]) == (m["group"], m["role"])


def index_row(d):
    """판 → 목차(digest_index.json)의 한 줄."""
    return {"date": d["date"], "status": d["status"], "must": len(d["must"]), "rest": sum(len(g["items"]) for g in d["rest"]),
            "posts": d["funnel"]["posts"], "channels_ok": d["sources"]["channels_ok"],
            "channels_total": d["sources"]["channels_total"], "collected_at": d["collected_at"]}


def next_streak(status, must_n, bond_new, prev):
    """꼭 볼 것 0건이 이어진 판 수. 정상 판에서만 센다 — 실린 것이 있으면 0, 없으면 +1(채권 채널의 새 글이 하나도 없던 날은 그대로)."""
    if status != "ok":
        return prev
    if must_n:
        return 0
    return prev + (1 if bond_new else 0)


# ---------- 머리 한 줄: 금리 범위 · 자료일 · 방향 칸 ----------

def _rate(key, rate, window):
    """금리 한 칸. 0~20 밖이면 버리고(None), fits는 자료일의 마감이 수집 창 안인지로 다시 셈한다."""
    if rate is None or not TH["rate_min"] < rate["value"] < TH["rate_max"]:
        return None
    chg = rate["chg_bp"]
    chg = None if chg is None or abs(chg) > TH["chg_bp_max"] else chg
    return {"value": rate["value"], "chg_bp": chg, "asof": rate["asof"], "fits": S.rate_fits(SERIES[key], rate["asof"], window)}


def _move(bp, names):
    """변화(bp) → 낱말. ±head_flat_bp 밖일 때만 방향을 적고 그 안은 보합. 변화를 모르면 None."""
    flat = TH["head_flat_bp"]
    return None if bp is None else names[0] if round(bp, 6) > flat else names[1] if round(bp, 6) < -flat else names[2]


def head_line(head, window):
    """공개할 머리 한 줄 — 앞 단계가 적어 온 fits · 방향 · 커브 · 종가 기준을 믿지 않고 숫자와 창으로 다시 만든다.
    국고 10년의 자료일이 창과 안 맞으면 방향을 비우고 '전일 종가', 10년·3년 중 하나라도 안 맞거나 두 자료일이 다르면 커브를 비운다.
    입력은 고치지 않는다."""
    kr10, kr3, us10 = (_rate(k, head[k], window) for k in ("kr10", "kr3", "us10"))
    fit10, fit3 = bool(kr10 and kr10["fits"]), bool(kr3 and kr3["fits"])
    both = fit10 and fit3 and kr10["asof"] == kr3["asof"] and kr10["chg_bp"] is not None and kr3["chg_bp"] is not None
    return {"kr10": kr10, "kr3": kr3, "us10": us10,
            "dir": _move(kr10["chg_bp"], R.DIRS) if fit10 else None,                        # 약세 = 금리 상승
            "curve": _move(kr10["chg_bp"] - kr3["chg_bp"], R.CURVES) if both else None,     # 스팁 = 10년−3년이 벌어짐
            "basis": None if kr10 is None else R.BASES[0] if fit10 else R.BASES[1], "top_terms": list(head["top_terms"])}


# ---------- 걸린 것만 빼기 (조립이 쓰기 전에, 검사가 '빼면 되는가'를 볼 때) ----------

def _url_code(x, roles, want):
    """링크·줄 하나(ch · url)를 내보낼 수 있는가 → None(괜찮음) · "url"(꼴이 다르거나 목록에 없는 채널) · "role"(이 자리에 올 수 없는 역할)."""
    m = S.URL_RE.fullmatch(x["url"]) if isinstance(x.get("url"), str) else None
    if not m or m.group("ch") != x.get("ch") or m.group("ch") not in roles:
        return "url"
    return None if roles[m.group("ch")] in want else "role"


def _ctx(sources, file):
    return {"roles": roles_of(sources), "handles": S.handles_of(sources), "file": file}


def _keep_item(x, where, ctx):
    """항목 하나 → (남길 항목 또는 None, 위반들). 못 쓰는 링크만 빼고, 링크가 남지 않거나 닫히지 않은 글자가 있으면 항목을 뺀다."""
    found, links = [], []
    for i, ln in enumerate(x["links"]):
        code = _url_code(ln, ctx["roles"], SOURCE)
        if code:
            found.append(_f(ctx["file"], f"{where}.links[{i}]", code, "link"))
        else:
            links.append(ln)
    new = {**x, "links": links}
    bad = [_f(ctx["file"], where + p[1:], "open", "item") for p in S.closed_violations(new, ctx["handles"])]
    if not links:
        bad.append(_f(ctx["file"], where, "empty", "item"))
    return (None if bad else new), found + bad


def keep_items(items, sources, where="$.must", file="digest.json"):
    """항목들 → (남길 항목들, 위반들)."""
    ctx, kept, found = _ctx(sources, file), [], []
    for i, x in enumerate(items):
        new, bad = _keep_item(x, f"{where}[{i}]", ctx)
        found += bad
        kept += [new] if new else []
    return kept, found


def _keep_rows(rows, where, want, ctx, names=None):
    """줄들 → (남길 줄들, 위반들). 주소·역할이 맞고 글자가 닫혀 있고, names를 주면 그 채널들의 줄만."""
    kept, found = [], []
    for i, r in enumerate(rows):
        code = _url_code(r, ctx["roles"], want)
        if code is None and names is not None and r["ch"] not in names:
            code = "role"
        opened = [] if code else S.closed_violations(r, ctx["handles"])
        found += [_f(ctx["file"], f"{where}[{i}]", code, "row")] if code else []
        found += [_f(ctx["file"], f"{where}[{i}]{p[1:]}", "open", "row") for p in opened]
        kept += [] if code or opened else [r]
    return kept, found


def keep_side(side, name, sources, file="digest.json"):
    """속보형(wire)·개인 단독(solo) 절 → (남길 절, 위반들). 그 절에 올 수 없는 채널과 그 채널의 줄을 뺀다."""
    ctx, chans, found = _ctx(sources, file), [], []
    for i, c in enumerate(side["channels"]):
        ok = ctx["roles"].get(c.get("ch")) in SIDES[name] and not S.closed_violations(c, ctx["handles"])
        chans += [c] if ok else []
        found += [] if ok else [_f(file, f"$.{name}.channels[{i}]", "role", "row")]
    rows, bad = _keep_rows(side["rows"], f"$.{name}.rows", SIDES[name], ctx, {c["ch"] for c in chans})
    return {"channels": chans, "rows": rows}, found + bad


def keep_context(rows, sources, file="digest.json"):
    """참고 줄 → (남길 줄들, 위반들)."""
    return _keep_rows(rows, "$.context", CONTEXT, _ctx(sources, file))


def prune(d, sources, file="digest.json"):
    """판에서 걸린 링크·줄·항목·금리 칸만 뺀 새 판과 그 위반들. 입력은 고치지 않는다."""
    must, found = keep_items(d["must"], sources, "$.must", file)
    rest = []
    for gi, g in enumerate(d["rest"]):
        items, bad = keep_items(g["items"], sources, f"$.rest[{gi}].items", file)
        found += bad
        rest += [{**g, "items": items}] if items else []
    sides = {}
    for name in SIDES:
        sides[name], bad = keep_side(d[name], name, sources, file)
        found += bad
    context, bad = keep_context(d["context"], sources, file)
    head = head_line(d["head"], d["window"])
    found += bad + [_f(file, f"$.head.{k}", "rate", "rate") for k in head if head[k] != d["head"].get(k)]
    out = {**d, "funnel": {**d["funnel"], "must": len(must)}, "head": head, "must": must, "rest": rest, **sides, "context": context}
    return out, found


def _where(e):
    """검증 오류 → 자리만(이유 문장은 버린다)."""
    return str(e).split(": ", 1)[0]


def check_edition(d, sources, file="digest.json"):
    """판 하나의 위반들. 뺄 수 있는 것(link · row · item · rate)을 먼저 찾고, 그것을 뺀 뒤에도 형식·글자·크기가 어긋나면 edition."""
    try:
        pruned, found = prune(d, sources, file)
        size = len(S.dump(d).encode("utf-8"))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return [_f(file, "$", "shape")]
    try:
        S.validate_digest(pruned, sources)
    except ValueError as e:
        found.append(_f(file, _where(e), "shape"))
    found += [_f(file, p, "open") for p in S.closed_violations(pruned, S.handles_of(sources))]
    return found + ([_f(file, "$", "size")] if size > EDITION_BYTES else [])


# ---------- 폴더 읽기 ----------

def list_files(public, strict=False):
    """공개 폴더 → (저녁판 파일 이름들, 계약에 없는 것의 수). 이름이 digest로 시작하는 것과 digest/ 아래만 본다
    (data/에는 아침 자료도 있다). strict면 폴더의 모든 이름을 본다 — 저녁판 파일이 아닌 것은 무엇이든 계약에 없는 것이다
    (아티팩트로 올라가는 폴더). 바로가기(심볼릭 링크)는 계약에 없는 것으로 친다."""
    def plain(*parts):
        path = os.path.join(public, *parts)
        return os.path.isfile(path) and not os.path.islink(path)
    top = sorted(os.listdir(public))
    names = [n for n in S.PUBLIC_FILES if n in top and plain(n)]
    known = ("digest",) if strict else ("digest", "digest_overrides.json")
    stray = sum((strict or n.startswith("digest")) and n not in names and n not in known for n in top)
    sub = os.path.join(public, "digest")
    if os.path.isdir(sub) and not os.path.islink(sub):
        days = sorted(os.listdir(sub))
        good = [n for n in days if DAY_FILE.fullmatch(n) and plain("digest", n)]
        return names + [f"digest/{n}" for n in good], stray + len(days) - len(good)
    return names, stray + ("digest" in top)


def _read(public, name):
    """파일 하나 → (바이트, 자료 또는 None, 위반 코드 또는 None). 기계가 쓴 파일은 다시 쓴 바이트와 같아야 한다 —
    겹친 칸이나 덧붙인 글자가 '검사한 자료'와 '나가는 바이트' 사이에 숨지 못하게."""
    with open(os.path.join(public, *name.split("/")), "rb") as f:
        raw = f.read()
    if len(raw) > TH["bytes_max"]:
        return raw, None, "size"
    try:
        doc = json.loads(raw.decode("utf-8"))
        same = S.dump(doc).encode("utf-8") == raw
    except (ValueError, RecursionError):               # 깨진 JSON · UTF-8이 아님 · 짝 없는 대리 문자
        return raw, None, "json"
    return raw, doc, None if same else "canon"


def check_file(name, doc, sources):
    """판이 아닌 파일(목차 · 상태 기록 · 갱신 상태) — 형식과 닫힌 글자."""
    try:
        S.validator_for(name)(doc)
    except ValueError as e:
        return [_f(name, _where(e), "shape")]
    return [_f(name, p, "open") for p in S.closed_violations(doc, S.handles_of(sources))]


def _human(public, sources):
    """사람이 쓰는 파일이 폴더에 같이 있으면(data/를 볼 때) 형식만 본다. 출처 목록은 라벨까지 닫혀 있어야 한다."""
    found = []
    for name in S.HUMAN_FILES:
        path = os.path.join(public, name)
        if not os.path.isfile(path):
            continue
        try:
            doc = S.validator_for(name)(S.read_json(path))
        except ValueError as e:
            found.append(_f(name, _where(e), "shape"))
            continue
        if name == "sources.json":
            labels = [c["label"] for c in doc["channels"]] + list(R.GROUPS.values()) + list(R.ROLES.values())
            found += [_f(name, p, "open") for p in S.closed_violations(doc, S.handles_of(doc, list(R.ROLES)), labels)]
    return found


# ---------- 파일끼리 · 수집 판정 · 0건 연속 ----------

def _cross(docs, raws):
    """판을 낸 날: 네 파일과 날짜별 판이 모두 있고 서로 같은 판을 가리키는가."""
    st = docs["digest_status.json"]
    day = f"digest/{st['edition']}.json"
    absent = [n for n in (*S.PUBLIC_FILES, day) if n not in raws]
    if absent:
        return [_f(n, "$", "missing") for n in absent]
    if any(n not in docs for n in (*S.PUBLIC_FILES, day)):
        return []                                      # 형식에서 이미 걸린 파일이 있다
    d, idx, ed = docs["digest.json"], docs["digest_index.json"], docs["digest_state.json"]["edition"]
    out = []
    if raws[day] != raws["digest.json"] or d["date"] != st["edition"]:
        out.append(_f(day, "$", "cross"))
    if next((e for e in idx["editions"] if e["date"] == d["date"]), None) != index_row(d):
        out.append(_f("digest_index.json", "$.editions", "cross"))
    if d["status"] == "withdrawn":
        same = not (ed and ed["must"])                 # 내린 날의 상태 기록은 지난 판 그대로일 수 있다 — 꼭 볼 것의 id만 없으면 된다
    else:
        same = bool(ed) and (ed["date"], ed["window"], ed["collected_at"], [m["id"] for m in ed["must"]]) == \
            (d["date"], d["window"], d["collected_at"], [x["id"] for x in d["must"]])
    return out + ([] if same else [_f("digest_state.json", "$.edition", "cross")])


def _health(st, d, groups):
    """수집 판정 — 채널별 숫자로 다시 낸 판정이 상태의 사유·판의 상태와 맞는가(수집 부족을 정상처럼 내지 않았는가)."""
    bad = [_f("digest_status.json", "$.reason", "coverage")]
    if st["reason"] == "error":
        return bad if st["published"] else []
    if st["reason"] == "withdrawn" or (d is not None and d["status"] == "withdrawn"):
        return [] if st["published"] and st["reason"] == "withdrawn" and d is not None and d["status"] == "withdrawn" else bad
    if any(c["ch"] not in groups for c in st["channels"]):
        return bad
    v = S.coverage_verdict([{**c, "group": groups[c["ch"]]} for c in st["channels"]])
    want = {"broken": ("broken",), "short": ("short",), "ok": ("ok", "empty_streak")}[v["verdict"]]
    ok = st["reason"] in want and st["counts"] == {k: v[k] for k in COUNT_KEYS} and st["published"] == (v["verdict"] != "broken")
    if ok and d is not None and st["published"]:
        ok = d["status"] == ("short" if v["verdict"] == "short" else "ok") and \
            d["sources"] == {"channels_ok": v["channels_ok"], "channels_total": v["channels_total"]}
    return [] if ok else bad


def _streak(st, state, d, groups):
    """0건 연속 — 공개된 숫자로 다시 센 값이 상태·상태 기록과 같고, 3판째면 사유가 empty_streak인가."""
    ed, base = state["edition"], state["base"]
    if d["status"] == "withdrawn" or not ed or ed["date"] != d["date"]:
        return []
    bond_new = sum(c["in_window"] for c in st["channels"] if c["ok"] and groups.get(c["ch"]) == "bond")
    want = next_streak(d["status"], len(d["must"]), bond_new, base["empty_streak"] if base else 0)
    flagged = d["status"] == "ok" and want >= TH["empty_streak_fail"]
    ok = st["empty_streak"] == want == ed["empty_streak"] and (st["reason"] == "empty_streak") == flagged
    return [] if ok else [_f("digest_status.json", "$.empty_streak", "streak")]


# ---------- 원문과 대조 (--raw) ----------

def _flat(s):
    return R.norm_text(s).casefold().replace(" ", "")


def _grams(texts):
    out = set()
    for t in map(_flat, texts):
        out.update(t[i:i + GRAM] for i in range(len(t) - GRAM + 1))
    return out


def _raw_index(raw):
    """원문 폴더 → 찾아보기. 원문은 이 함수와 아래 대조 함수 밖으로 나가지 않는다(출력에 싣지 않는다)."""
    doc = S.validate_posts_doc(S.read_json(os.path.join(raw, "posts.json")))
    posts = doc["posts"]
    texts = [x for p in posts for x in (p["text"], *p["links"], *(p["card"] or {}).values())]
    return {"doc": doc, "by": {(p["ch"], p["id"]): p for p in posts}, "grams": _grams(texts),
            "terms": {t["term"] for p in posts for t in R.match_terms(p["text"])},
            "nums": {n["v"] for p in posts for n in R.find_nums(p["text"])}}


def _post_of(x, by):
    """링크·줄이 가리키는 글 — 이 실행에서 수집됐고 올린 시각이 같을 때만."""
    m = S.URL_RE.fullmatch(x["url"])
    p = by.get((m.group("ch"), int(m.group("id")))) if m else None
    return p if p and p["at"] == x["at"] else None


def _row_in(r, p):
    """줄의 낱말·결과 낱말·숫자가 그 글에 있는가."""
    return r["term"] in {t["term"] for t in R.match_terms(p["text"])} and r["v"] in {n["v"] for n in R.find_nums(p["text"])} \
        and (r["result"] is None or r["result"] in {x["result"] for x in R.match_results(p["text"])})


def _against_raw(name, d, ix):
    """판과 원문 — 같은 실행의 것인가, 링크·줄의 글이 수집됐는가, 항목과 줄의 낱말·숫자가 글에 있는가."""
    if d["status"] == "withdrawn":
        return []
    if (d["date"], d["window"]) != (ix["doc"]["edition"], ix["doc"]["window"]):
        return [_f(name, "$.window", "cross")]
    out = []
    items = [(f"$.must[{i}]", x) for i, x in enumerate(d["must"])]
    items += [(f"$.rest[{gi}].items[{i}]", x) for gi, g in enumerate(d["rest"]) for i, x in enumerate(g["items"])]
    for where, x in items:
        out += [_f(name, f"{where}.links[{i}]", "unseen", "link") for i, ln in enumerate(x["links"]) if not _post_of(ln, ix["by"])]
        words = set(x["terms"]) | {n["term"] for n in x["nums"]}
        if not (words <= ix["terms"] and {n["v"] for n in x["nums"]} <= ix["nums"]):
            out.append(_f(name, where, "mismatch", "item"))
    for side in SIDES:
        for i, r in enumerate(d[side]["rows"]):
            p = _post_of(r, ix["by"])
            if p is None or not _row_in(r, p):
                out.append(_f(name, f"$.{side}.rows[{i}]", "mismatch" if p else "unseen", "row"))
    return out + [_f(name, f"$.context[{i}]", "unseen", "row") for i, r in enumerate(d["context"]) if not _post_of(r, ix["by"])]


def _strings_at(doc, at, handles):
    """위반 자리의 글자들 — 닫히지 않은 값, 정해지지 않은 칸이면 그 객체의 모르는 칸 이름과 그 아래 값."""
    node = doc
    try:
        for key, idx in _STEP.findall(at[1:]):
            if key == UNKNOWN:
                return [s for k, v in node.items() if k not in S.FIELDS and k not in handles
                        for s in (k, json.dumps(v, ensure_ascii=False))]
            node = node[int(idx)] if idx else node[key]
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return []
    return [node] if isinstance(node, str) else []


def _name_leaks(found, loaded, ix, handles):
    """닫히지 않은 글자(open) 가운데 원문과 GRAM자 이상 겹치는 것을 leak으로 바꿔 부른다."""
    out = []
    for f in found:
        doc = loaded.get(f["file"])
        hit = f["code"] == "open" and doc is not None and bool(_grams(_strings_at(doc, f["at"], handles)) & ix["grams"])
        out.append({**f, "code": "leak"} if hit else f)
    return out


def _raw_checks(raw, found, loaded, docs, sources):
    """--raw: 원문과 맞춰 본 위반을 더한다. 건강 숫자는 수집 기록(collect_status.json)과 같아야 한다."""
    ix = _raw_index(raw)
    found = _name_leaks(found, loaded, ix, S.handles_of(sources))
    for name, d in docs.items():
        if name == "digest.json" or name.startswith("digest/"):
            found += _against_raw(name, d, ix)
    st, path = docs.get("digest_status.json"), os.path.join(raw, "collect_status.json")
    if st and st["reason"] not in ("withdrawn", "error") and os.path.isfile(path):
        cs = S.validate_collect_status(S.read_json(path))
        if (cs["edition"], [{k: c[k] for k in CHAN_KEYS} for c in cs["channels"]]) != (st["edition"], st["channels"]):
            found.append(_f("digest_status.json", "$.channels", "cross"))
    return found


# ---------- 폴더 검사 · 실행 ----------

def check_folder(public, sources, raw=None, strict=False):
    """공개 폴더 하나 → (위반들, {files, published, reason, edition}). 위반이 비어 있어야 내보낼 수 있다.
    strict = 폴더에 저녁판 파일 말고 아무것도 없어야 한다(아티팩트로 올라가는 폴더)."""
    names, stray = list_files(public, strict)
    found, raws, loaded, docs = [_f(STRAY, "$", "stray")] * stray, {}, {}, {}
    for name in names:
        raws[name], doc, code = _read(public, name)
        bad = [_f(name, "$", code)] if code else []
        if doc is not None:
            loaded[name] = doc
            day = name == "digest.json" or name.startswith("digest/")
            bad += check_edition(doc, sources, name) if day else check_file(name, doc, sources)
        if not bad:
            docs[name] = doc                           # 위반이 하나도 없는 파일만 서로 맞춰 본다
        found += bad
    found += _human(public, sources)
    st, groups = docs.get("digest_status.json"), {c["handle"]: c["group"] for c in sources["channels"]}
    if "digest_status.json" not in raws:
        found.append(_f("digest_status.json", "$", "missing"))
    if st:
        found += _cross(docs, raws) if st["published"] else []
        found += _health(st, docs.get("digest.json"), groups)
        if st["published"] and "digest.json" in docs and "digest_state.json" in docs:
            found += _streak(st, docs["digest_state.json"], docs["digest.json"], groups)
    if raw:
        found = _raw_checks(raw, found, loaded, docs, sources)
    facts = {"files": len(names), "published": bool(st and st["published"]), "reason": st["reason"] if st else None,
             "edition": st["edition"] if st else None}
    return found, facts


def _safe(at, handles):
    """자리 문자열에서 칸 이름·목록의 채널 이름이 아닌 토막을 가린다(채널 이름 꼴의 칸에 다른 글자가 실려 오지 않게)."""
    ok = S.FIELDS | ROOTS | set(handles)
    return _WORD.sub(lambda m: m.group(0) if m.group(0) in ok else "?", at)


def main(argv=None):
    ap = argparse.ArgumentParser(description="저녁판 공개 폴더 검사 — 형식 · 닫힌 글자 · 금리 범위 · 수집 판정 · 0건 연속 (읽기만 한다)")
    ap.add_argument("--public", required=True, help="검사할 폴더 (digest.json · digest/<날짜>.json · digest_index · _state · _status)")
    ap.add_argument("--raw", default=None, help="원문 폴더(.work/evening) — 주면 링크의 글이 수집됐는지, 낱말·숫자가 글에 있는지도 본다")
    ap.add_argument("--sources", default=os.path.join(S.DATA, "sources.json"), help="출처 목록 (기본: 저장소의 data/sources.json)")
    ap.add_argument("--strict", action="store_true", help="폴더에 저녁판 파일 말고 아무것도 없어야 한다(아티팩트로 올라가는 폴더)")
    ap.add_argument("--alert", action="store_true", help="위반이 없어도 상태가 실패(수집 부족 · 0건 연속 · 형식 바뀜 · 실행 실패)면 종료코드 2")
    a = ap.parse_args(argv)
    sources = S.validate_sources(S.read_json(a.sources))
    found, facts = check_folder(os.path.abspath(a.public), sources, os.path.abspath(a.raw) if a.raw else None, a.strict)
    handles = S.handles_of(sources)
    for f in found[:MAX_LINES]:
        print(f"[digest_check] 위반 file={f['file']} code={f['code']} scope={f['scope']} at={_safe(f['at'], handles)}")
    S.report("digest_check", **{k: v for k, v in facts.items() if v is not None}, violations=len(found))
    if found:
        return 1
    return 2 if a.alert and facts["reason"] in ALERT_REASONS else 0


if __name__ == "__main__":
    sys.exit(S.run_cli("digest_check", main))
