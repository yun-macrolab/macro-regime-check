#!/usr/bin/env python3
"""저녁판 미리 보기 — site/ 사본과 판을 한 폴더로 조립한다 (2026-10-08). 화면(site/evening.js)을 눈으로 확인할 때 쓴다.

  python scripts/evening/preview.py [--case ok] [--date YYYY-MM-DD] [--ai] [--out .work/evening/preview]
  python scripts/evening/preview.py --from .work/evening/public [--data data] [--picks <요약 층 파일>] [--out .work/evening/preview]
  python -m http.server 8765 --directory .work/evening/preview      →  http://localhost:8765/#evening

--from을 주지 않으면 fixtures.py의 지어낸 글로 만든 판이고 채널도 가짜 이름이다. 판 날짜는 오늘에 맞춰 옮긴다(그대로 두면 화면이
'판이 아직 없습니다'를 띄운다). 가짜 채널 주소가 들어 있으므로 저장소 안에서는 .work/ 아래에만 쓴다 — data/ · site/에는 쓰지 않는다.
아침 화면도 같이 뜨도록 data/의 아침 자료(public.json 등)는 있는 대로 옮겨 둔다.

  --case  ok 꼭 3건 · fewer 2건 · none 0건 · short 수집 부족 · partial 채널 1곳 실패 · hidden 숨김 목록 ·
          withdrawn 내린 판 · late 오늘 판이 아직 없음 · failed 실행 실패(직전 판 유지) · empty 판 파일 없음
  --from  PC 시범 실행(evening_run.py pipeline --out <폴더>)이 낸 공개 JSON 폴더를 그대로 본다. 출처 목록·일정표·숨김 파일은
          --data(기본: 저장소의 data/)에서 읽고, 날짜는 옮기지 않는다. 검사(digest_check)를 통과한 폴더만 받는다 —
          내보낼 수 없는 것은 미리 보지도 않는다. 게시가 아니다: 조립한 것은 .work/ 아래에만 있다.
  --ai    지어낸 판에 지어낸 AI 요약 문장(fixtures.picks)을 같이 둔다 — 화면이 문장을 어떻게 붙이는지 볼 때
  --picks AI 요약 층 파일(evening_llm.py --dry-run이 .work/ 아래에 쓴 digest_picks.json 같은 것)을 같이 둔다. 형식 검사
          (digest_picks.validate_picks)를 통과한 것만 받는다. 주지 않으면 요약 층 없이 조립한다(data/에 올라간 것을 따라 읽지 않는다).
"""
import argparse
import copy
import datetime
import functools
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import digest_check as C
import digest_picks as K
import digest_rules as R
import digest_schema as S
import fixtures as F

CASES = ("ok", "fewer", "none", "short", "partial", "hidden", "withdrawn", "late", "failed", "empty")
OUT = os.path.join(S.WORK, "preview")
EVENING = ("digest.json", "digest_index.json", "digest_status.json", "digest_state.json", "sources.json", "calendar.json",
           "digest_overrides.json", K.FILE)            # 미리 보기가 직접 쓰는 이름 — 아침 자료를 옮길 때 건너뛴다
_ISO = re.compile(r"^(\d{4}-\d{2}-\d{2})(T\d{2}:\d{2}:\d{2}\+09:00)$")


@functools.lru_cache(maxsize=None)
def _made(name):
    return getattr(F, name)()


def _fx(name):
    """fixtures의 자료 하나 — 한 번만 만들고 사본을 돌려준다(판 하나 만드는 데 0.1초쯤 든다)."""
    return copy.deepcopy(_made(name))


# ---------- 날짜 옮기기 ----------


def _move(day, days):
    return (datetime.date.fromisoformat(day) + datetime.timedelta(days=days)).isoformat()


def shift(obj, days):
    """자료 안의 날짜 · 시각 · 항목 id의 날짜를 days일 옮긴 새 자료(받은 자료는 고치지 않는다)."""
    if isinstance(obj, dict):
        return {k: shift(v, days) for k, v in obj.items()}
    if isinstance(obj, list):
        return [shift(v, days) for v in obj]
    if not isinstance(obj, str):
        return obj
    m = _ISO.match(obj)
    if m:
        return _move(m.group(1), days) + m.group(2)
    if S.DATE_RE.match(obj):
        return _move(obj, days)
    if S.ID_RE.match(obj):
        return _move(f"{obj[:4]}-{obj[4:6]}-{obj[6:8]}", days).replace("-", "") + obj[8:]
    return obj


def back(day, n=1):
    """평일로 n일 거슬러 간 날."""
    for _ in range(n):
        day -= datetime.timedelta(days=1)
        while day.weekday() > 4:
            day -= datetime.timedelta(days=1)
    return day


def edition_day(now):
    """미리 볼 판 날짜 — 지금의 판 날짜에서 평일이 될 때까지 거슬러 간 날(주말판은 없다)."""
    day = datetime.date.fromisoformat(S.edition_date(now))
    return day if day.weekday() < 5 else back(day)


# ---------- 경우별 판 ----------


def _fewer(d, n):
    notes = [R.phrase("note_fewer", n=n)] if n else [R.phrase("note_none")]
    funnel = {**d["funnel"], "must": n, "candidates": min(d["funnel"]["candidates"], n)}
    out = {**d, "must": d["must"][:n], "funnel": funnel, "notes": notes}
    return {**out, "gloss": R.glosses(S.shown_terms(out))}            # 풀이는 이 판에 나온 낱말의 것만 실린다


def _unread(status, fail):
    """상태 파일에서 fail = {채널: 코드}의 채널을 못 읽은 것으로 바꾼 새 상태."""
    chans = [{**c, "ok": False, "code": fail[c["ch"]], "posts": 0, "with_text": 0, "in_window": 0, "fail_streak": 1}
             if c["ch"] in fail else c for c in status["channels"]]
    bond = sum(c["ok"] and F.GROUP[c["ch"]] == "bond" for c in chans)
    counts = {**status["counts"], "channels_ok": sum(c["ok"] for c in chans), "bond_ok": bond}
    return {**status, "channels": chans, "counts": counts}


def _variant(case):
    """경우 하나의 (판, 상태, 숨김 목록) — 날짜는 fixtures의 것 그대로."""
    d, st, ov = _fx("digest"), _fx("status"), F.overrides()
    if case == "fewer":
        d = _fewer(d, 2)
    elif case == "none":
        d = _fewer(d, 0)
    elif case == "short":
        lost = {ch: "fetch" for ch in F.REQUESTED if F.GROUP[ch] == "personal"}
        st = {**_unread(st, lost), "ok": False, "reason": "short"}
        d = {**_fewer(d, 0), "status": "short", "notes": [R.phrase("note_short")],
             "sources": {**d["sources"], "channels_ok": st["counts"]["channels_ok"]}}
    elif case == "partial":
        st = _unread(st, {"fxbond3": "fetch"})
        d = {**d, "sources": {**d["sources"], "channels_ok": st["counts"]["channels_ok"]}, "notes": [R.phrase("note_channels", n=1)]}
    elif case == "hidden":
        ov = F.overrides(hide_ids=[d["must"][1]["id"]], hide_channels=["fxpers2"])
    elif case == "withdrawn":
        d = S.blank_digest(S.parse_iso(F.NOW))
        st = {**st, "ok": False, "reason": "withdrawn"}
    elif case == "failed":
        st = {**st, "ok": False, "reason": "broken", "published": False}
    return d, st, ov


def _row(d):
    return {"date": d["date"], "status": d["status"], "must": len(d["must"]), "rest": sum(len(g["items"]) for g in d["rest"]),
            "posts": d["funnel"]["posts"], **d["sources"], "collected_at": d["collected_at"]}


def _days(a, b):
    return (b - a).days


def build(case="ok", day=None, now=None, ai=False):
    """미리 볼 자료 {data/ 아래 경로: 자료}. day = 맨 앞 판의 날짜(없으면 지금에 맞춘다). 쓰기 전에 형태를 검증한다.
    ai면 지어낸 AI 요약 층을 맨 앞 판의 날짜로 같이 둔다(그 판에 없는 항목의 문장은 화면이 붙이지 않는다)."""
    if case not in CASES:
        raise ValueError("없는 경우")
    now = now or datetime.datetime.now(S.KST)
    today = day or edition_day(now)
    base = datetime.date.fromisoformat(F.EDITION)
    docs = {"sources.json": _fx("sources"), "calendar.json": _fx("calendar")}
    d, st, ov = _variant(case)
    if case == "empty":
        return _checked({**docs, "digest_overrides.json": ov})
    first = back(today, 2) if case == "late" else back(today) if case == "failed" else today      # 화면에 뜨는 맨 앞 판
    ran = today if case == "failed" else first                                                    # 상태 파일이 말하는 마지막 실행
    old = [_fewer(_fx("digest"), 2), _variant("short")[0], _fewer(_fx("digest"), 0)]              # 지난 판 셋(넘겨 볼 것)
    editions = [shift(d, _days(base, first))] + [shift(x, _days(base, back(first, n + 1))) for n, x in enumerate(old)]
    for e in editions:
        docs[f"digest/{e['date']}.json"] = e
    docs["digest.json"] = editions[0]
    docs["digest_overrides.json"] = shift(ov, _days(base, first))                                 # 숨김 id의 날짜도 판과 같이 옮긴다
    docs["digest_index.json"] = {"schema": S.SCHEMA, "updated_at": editions[0]["collected_at"], "latest": editions[0]["date"],
                                 "editions": [_row(e) for e in editions]}
    last = {"date": editions[0]["date"], "at": editions[0]["collected_at"]}
    docs["digest_status.json"] = {**shift(st, _days(base, ran)), "last_success": last}
    if ai:
        docs[K.FILE] = shift(_fx("picks"), _days(base, first))
    return _checked(docs)


def _checked(docs):
    for name, doc in docs.items():
        if name == K.FILE:                            # AI 요약 층은 규칙판의 계약 밖이다 — 제 검증으로 본다
            K.validate_picks(doc, docs["sources.json"])
        elif S.validator_for(name) is S.validate_digest:
            S.validate_digest(doc, docs["sources.json"])
        else:
            S.validator_for(name)(doc)
    return docs


def real(public, data=S.DATA, picks=None):
    """파이프라인이 낸 공개 폴더 + 사람이 쓰는 파일(<data>의 출처 목록 · 일정표 · 숨김) → 미리 볼 자료 {data/ 아래 경로: 자료}.
    낸 그대로다(날짜를 옮기지 않는다). 검사에 걸리는 폴더면 ValueError — 위반의 자리와 값은 싣지 않는다.
    picks = AI 요약 층 파일의 경로(있으면 같이 둔다 — 형식에 안 맞으면 ValueError)."""
    human = {name: S.read_json(os.path.join(data, name)) for name in S.HUMAN_FILES}
    sources = S.validate_sources(human["sources.json"])
    found, _ = C.check_folder(os.path.abspath(public), sources)
    if found:
        raise ValueError("검사에 걸린 폴더는 미리 보지 않음")
    names, _ = C.list_files(public)
    extra = {K.FILE: S.read_json(picks)} if picks else {}
    return _checked({**human, **{name: S.read_json(os.path.join(public, *name.split("/"))) for name in names}, **extra})


# ---------- 폴더 조립 ----------


def _inside(path, root):
    a, b = (os.path.normcase(os.path.abspath(p)) for p in (path, root))
    try:
        return os.path.commonpath([a, b]) == b
    except ValueError:                                # 드라이브가 다르다
        return False


def assemble(out, docs):
    """site/ 사본 + 아침 자료(있는 대로) + 미리 볼 자료를 out에 쓴다 → 쓴 저녁 자료 수. 저장소 안이면 .work/ 아래만 받는다."""
    out = os.path.abspath(out)
    if _inside(out, S.REPO) and not _inside(out, os.path.join(S.REPO, ".work")):
        raise ValueError("미리 보기 폴더는 저장소 안에서는 .work/ 아래여야 함")
    data, past = os.path.join(out, "data"), os.path.join(out, "data", "digest")
    shutil.copytree(os.path.join(S.REPO, "site"), out, dirs_exist_ok=True)
    os.makedirs(past, exist_ok=True)
    for name in os.listdir(S.DATA) if os.path.isdir(S.DATA) else []:
        if name.endswith(".json") and name not in EVENING:
            shutil.copy2(os.path.join(S.DATA, name), os.path.join(data, name))
    stale = [os.path.join(data, n) for n in EVENING]
    stale += [os.path.join(past, n) for n in os.listdir(past) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", n)]
    for path in stale:                                # 앞서 조립한 판을 치운다(판 파일이 없는 경우도 볼 수 있게)
        if os.path.isfile(path):
            os.remove(path)
    for name, doc in docs.items():
        S.write_json(os.path.join(data, *name.split("/")), doc)
    return len(docs)


def main(argv=None):
    ap = argparse.ArgumentParser(description="저녁판 화면을 미리 볼 폴더를 조립한다(지어낸 판, 또는 --from으로 시범 실행이 낸 판)")
    ap.add_argument("--case", default="ok", choices=CASES, help="보고 싶은 경우 (기본: ok)")
    ap.add_argument("--date", help="맨 앞 판의 날짜 YYYY-MM-DD (기본: 오늘에 맞춘다)")
    ap.add_argument("--from", dest="source", help="시범 실행이 낸 공개 JSON 폴더 — 주면 지어낸 판 대신 그것을 그대로 본다")
    ap.add_argument("--data", default=S.DATA, help="--from일 때 출처 목록 · 일정표 · 숨김 파일을 읽을 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--ai", action="store_true", help="지어낸 판에 지어낸 AI 요약 문장을 같이 둔다")
    ap.add_argument("--picks", help="--from일 때 같이 둘 AI 요약 층 파일(digest_picks.json) — 형식 검사를 통과한 것만")
    ap.add_argument("--out", default=OUT, help="쓸 폴더 (기본: .work/evening/preview)")
    a = ap.parse_args(argv)
    day = datetime.date.fromisoformat(a.date) if a.date else None
    docs = real(a.source, a.data, a.picks) if a.source else build(a.case, day, ai=a.ai)
    n = assemble(a.out, docs)
    S.report("preview", files=n, editions=sum(name.startswith("digest/") for name in docs))
    print('  python -m http.server 8765 --directory "' + os.path.abspath(a.out).replace(os.sep, "/") + '"')
    print("  http://localhost:8765/#evening")
    return 0


if __name__ == "__main__":
    sys.exit(S.run_cli("preview", main))
