#!/usr/bin/env python3
"""저녁판 조립 — 점수 붙은 묶음(scored.json)을 공개 JSON으로 (2026-10-08, 1단계 규칙 선별판).

원문을 읽지 않는다. 입력(scored.json · collect_status.json)에는 닫힌 값만 있고(사전 낱말 · 숫자+단위 · 시각 · 채널 이름 · 글 번호 · 해시),
여기서 나가는 것도 그것과 고정 문구, 채널 이름 + 글 번호로 조립한 주소뿐이다. 규칙은 방향·강도를 내지 않는다.

쓰는 것 (<out>/ — 전부 검사한 뒤에 쓴다. 하나라도 어긋나면 아무것도 쓰지 않는다)
  digest.json · digest/<판 날짜>.json  오늘 판(둘은 바이트까지 같다) — 꼭 볼 것 3건까지, 나머지 표 30줄까지, 속보형·개인 단독 줄, 내일 볼 것
  digest_index.json                   날짜별 판의 목차, 최신순 35일. 같은 판 날짜를 다시 돌면 그 줄을 바꿔 넣는다
  digest_state.json                   이번 판(edition)과 그 직전 판(base)의 기록 — 채널별 마지막 글 번호·시각·연속 실패, 수집 창,
                                      꼭 볼 것의 id·열쇠(해시), 0건이 이어진 판 수. 같은 날 다시 돌아도 base는 그대로다
  digest_status.json                  갱신 상태 — 사유, 채널별 읽기 건강 숫자, 마지막 정상 판, 화면이 '아직 없다'를 정할 시각

같은 입력이면 같은 바이트다(시계를 읽지 않는다 — 시각은 수집 기록의 것). 낸 것을 입력 삼아 같은 자료를 다시 돌려도 같다.

판을 만들 때 하는 일
  수집 판정   broken(본문 비율이 절반 아래 — 미리보기 형식이 바뀐 것)이면 판을 내지 않고 상태만 쓴다(종료코드 3).
              short(채권 3곳 미만 또는 전체 16곳 미만)이면 꼭 볼 것을 비우고 그 묶음들을 나머지 표로 내린다(종료코드 2).
  숨김       digest_overrides.json — hide_ids의 항목은 빼고 그 자리를 다른 묶음으로 채우지 않는다. hide_channels의 채널은 링크·줄·
              씨앗 글에서 뺀다(id도 보이는 글로 다시 만든다). withdraw면 빈 판(status withdrawn)을 낸다.
  출처 목록   지금 목록(sources.json)에 같은 그룹·역할로 있는 채널의 글만 링크·줄이 된다. 목록에서 뺀 채널은 상태 기록에서도 뺀다.
  머리 한 줄  금리 칸은 scored.json의 것을 받아 자료일을 수집 창과 다시 맞춘다(digest_check.head_line) — 국고 10년의 자료일이
              창 밖이면 방향을 비우고 '전일 종가'. korea.json은 점수 단계가 읽고, 여기서는 읽지 않는다.
  내일 볼 것  scored.json의 일정 가운데 창이 끝난 뒤부터 tomorrow_days일 안의 것만(오늘 밤 일정 포함), 날짜·시각순.
  크기       나머지 표는 30줄까지, 판 하나는 20KB(digest_check.EDITION_BYTES)까지 — 넘으면 점수가 낮은 줄부터 줄이고 줄인 수를 적는다.
  0건 연속   꼭 볼 것이 0건인 정상 판이 3판 이어지면 실행을 실패로 끝낸다(종료코드 2 — 빈 판이 조용히 이어지지 않게).
              채권 채널의 새 글이 하나도 없던 날은 세지 않는다.
  채널 바뀜   제목 해시가 다르거나 글 번호가 거꾸로 간 채널(수집이 뺀 채널)이 있으면 판은 내되 종료코드 2.
  안 읽히는 채널  채권 채널이 fail_streak_alert판 이어서 안 읽히면 판은 내되 종료코드 2(화면의 한 줄로만 남아 조용히 이어지지 않게).
  읽은 곳     상태 기록의 read_to = '여기까지 제대로 읽었다'. 정상 판·내린 판은 창의 끝, 수집 부족 판은 직전 판의 값 그대로 —
              다음 판의 수집 창이 거기서 시작해 그날 못 읽은 글을 다시 읽는다.

사용법: python scripts/evening/digest_build.py --work .work/evening --out <폴더> [--data data]
        ... --blank [--now ISO]   내리기 전용: 수집한 것 없이 빈 판을 쓰고, <out>/digest/의 지난 판과 목차·꼭 볼 것의 id를 지운다.
                                   출처 목록·상태 파일이 깨져 있어도 돈다(그때는 상태 기록을 비운다)
        ... --error [--now ISO]   실행이 실패한 날: 판 없이 상태(reason error)만 쓴다
종료코드: 0 판을 냄(내린 판 포함) / 2 판은 냈지만 실행을 실패로 끝낼 것 / 3 판을 내지 않고 상태만 씀 / 1 실패(아무것도 쓰지 않음)
"""
import argparse
import datetime
import os
import sys

import digest_check as C
import digest_rules as R
import digest_schema as S

TH = S.TH
EMPTY_STATE = {"schema": S.SCHEMA, "edition": None, "base": None}
EMPTY_OVERRIDES = {"schema": S.SCHEMA, "withdraw": False, "hide_ids": [], "hide_channels": []}
OTHER_CELL = {"factor": "기타", "region": "글로벌"}      # 사전 낱말이 하나도 없는 묶음(채권 채널이 혼자 쓴 글 등)이 가는 칸
CHANGED = ("title", "rewind")                           # 채널이 다른 곳으로 넘어갔을 수 있다는 수집 코드
ORDER = ("digest.json", "digest_index.json", "digest_state.json", "digest_status.json")    # 쓰는 순서 — 상태가 마지막


# ---------- 항목 ----------

def _visible(c, roles, hidden):
    """묶음의 글 가운데 내보낼 수 있는 것 — 지금 목록에 같은 그룹·역할로 있고, 숨긴 채널이 아닌 글."""
    return [m for m in c["members"] if C.member_ok(m, roles) and m["ch"] not in hidden]


def _shown_terms(c, limit):
    """항목에 싣는 낱말 — 여러 채널이 든 묶음은 두 곳 이상이 쓴 낱말만(없으면 대표 낱말 하나), 한 채널뿐인 묶음은 그대로.
    한 곳만 쓴 낱말(끼어든 글의 낱말일 수 있다)이 항목의 제목이 되지 않게 한다."""
    names = [t["term"] for t in c["terms"]]
    if len({m["ch"] for m in c["members"]}) > 1:
        names = [t["term"] for t in c["terms"] if t["n_ch"] >= TH["k_result_min_ch"]] or names[:1]
    return names[:limit]


def _item(c, date, members, must):
    """묶음 → 공개 항목. id는 보이는 글의 씨앗 글로, 링크는 링크 순서 규칙(S.pick_links)으로. 보이는 원천 글이 없으면 None."""
    if not any(m["role"] == "source" for m in members):
        return None
    seed = S.seed_of(members)
    base = {"id": S.item_id(date, seed["ch"], seed["id"]), "key": c["key"], "cell": dict(c["cell"] or OTHER_CELL)}
    if must:
        return {**base, "terms": _shown_terms(c, TH["terms_max"]), "nums": [dict(n) for n in c["nums"][:TH["nums_max"]]],
                "score": dict(c["score"]), "why": list(c["why"][:TH["why_max"]]), "coverage": dict(c["coverage"]),
                "links": S.pick_links(members)}
    return {**base, "terms": _shown_terms(c, TH["rest_terms_max"]), "nums": [dict(n) for n in c["nums"][:TH["rest_nums_max"]]],
            "s": c["score"]["total"], "coverage": dict(c["coverage"]), "links": S.pick_links(members, TH["rest_links_max"])}


def _items(clusters, date, roles, hidden, hide_ids, must):
    """묶음들 → [(항목, 묶음)]. 숨긴 항목은 빼고, 그 자리를 다른 묶음으로 채우지 않는다."""
    out = []
    for c in clusters:
        x = _item(c, date, _visible(c, roles, hidden), must)
        if x and x["id"] not in hide_ids:
            out.append((x, c))
    return out


def _pick(clusters, short):
    """(꼭 볼 묶음들 순위순, 나머지 묶음들 점수순). 수집 부족이면 꼭 볼 것을 비우고 그 묶음들을 나머지 표로 내린다."""
    must = sorted((c for c in clusters if c["pick"] == "must"), key=lambda c: c["rank"])
    rest = [c for c in clusters if c["pick"] == "rest"] + (must if short else [])
    rest.sort(key=lambda c: (-c["score"]["total"], c["first_at"], c["seed"]["ch"], c["seed"]["id"]))
    return ([] if short else must), rest


# ---------- 속보형 · 개인 단독 · 참고 · 내일 볼 것 ----------

def _row(m):
    """혼자 쓴 글 하나 → 줄(낱말 · 결과 낱말 · 숫자 · 시각 · 주소). 묶기 단계가 지은 짝(row — 첫머리의 첫 숫자와 그 앞의 가까운 A·B급
    낱말)이 있을 때만 줄이 된다. 한 곳만 쓴 숫자라서 시세 수준·긴 숫자는 묶기 단계가 이미 걸렀다(R.solo_num_ok)."""
    pair = m.get("row")
    if not pair:
        return None
    return {"ch": m["ch"], "term": pair["term"], "result": m["results"][0] if m["results"] else None, "v": pair["v"],
            "at": m["at"], "url": S.post_url(m["ch"], m["id"])}


def _side(scored, collect, roles, hidden, want):
    """속보형(wire)·개인 단독(solo) 절 — 읽힌 채널마다 읽은 글(read) · 다른 채널과 묶인 글(joined) · 줄이 될 수 있었던 글(hit).
    줄은 채널당 rows_per_channel개까지, 이른 글부터."""
    chans = {c["ch"]: {"ch": c["ch"], "read": c["in_window"], "joined": 0, "hit": 0} for c in collect["channels"]
             if c["ok"] and roles.get(c["ch"]) in want and c["ch"] not in hidden}
    rows = []
    for c in scored["clusters"]:
        alone = len({m["ch"] for m in c["members"]}) == 1
        for m in _visible(c, roles, hidden):
            row = _row(m) if alone and c["pick"] == "none" else None
            if m["ch"] in chans:
                chans[m["ch"]]["joined"] += not alone
                chans[m["ch"]]["hit"] += row is not None
                rows += [row] if row else []
    rows.sort(key=lambda r: (r["at"], r["ch"], r["url"]))
    seen, out = {}, []
    for r in rows:
        seen[r["ch"]] = seen.get(r["ch"], 0) + 1
        out += [r] if seen[r["ch"]] <= TH["rows_per_channel"] else []
    return {"channels": sorted(chans.values(), key=lambda r: r["ch"]), "rows": out}


def _context(scored, roles, hidden):
    """참고 채널(주식 시황 확인용)의 글 — 점수에는 넣지 않고 링크 한 줄씩, 가장 늦은 context_max개."""
    rows = [{"ch": m["ch"], "at": m["at"], "url": S.post_url(m["ch"], m["id"])}
            for c in scored["clusters"] for m in _visible(c, roles, hidden) if m["role"] == "context"]
    return sorted(rows, key=lambda r: (r["at"], r["ch"], r["url"]))[-TH["context_max"]:]


def _tomorrow(rows, window):
    """내일 볼 것 — 점수 단계가 고른 일정 가운데 창이 끝난 뒤부터 tomorrow_days일 안의 것만(오늘 밤 일정 포함), 날짜·시각순."""
    to = S.parse_iso(window["to"])
    last = (to.date() + datetime.timedelta(days=TH["tomorrow_days"])).isoformat()
    keep = [{**r, "detail": list(r["detail"])} for r in rows
            if r["date"] <= last and S.parse_iso(f"{r['date']}T{r['time'] or '23:59'}:00+09:00") > to]
    return sorted(keep, key=lambda r: (r["date"], r["time"] or "99:99"))[:TH["tomorrow_max"]]


# ---------- 판 ----------

def _parts(scored, collect, sources, overrides):
    """판에 실을 재료 → (재료, {항목 id: 묶음})."""
    roles, hidden, date = C.roles_of(sources), set(overrides["hide_channels"]), scored["edition"]
    must_c, rest_c = _pick(scored["clusters"], collect["verdict"] == "short")
    must = _items(must_c, date, roles, hidden, overrides["hide_ids"], True)
    rest = _items(rest_c, date, roles, hidden, overrides["hide_ids"], False)
    parts = {"must": [x for x, _ in must], "rest": [x for x, _ in rest],
             "wire": _side(scored, collect, roles, hidden, C.SIDES["wire"]),
             "solo": _side(scored, collect, roles, hidden, C.SIDES["solo"]),
             "context": _context(scored, roles, hidden), "head": C.head_line(scored["head"], scored["window"]),
             "tomorrow": _tomorrow(scored["tomorrow"], scored["window"])}
    return parts, {x["id"]: c for x, c in must + rest}


def _guard(parts, sources):
    """쓰기 전의 마지막 거름 — 검사에 걸릴 링크·줄·항목을 미리 뺀다(설계 8절: 걸린 것만 뺀다). → (재료, 뺀 것의 수)"""
    must, a = C.keep_items(parts["must"], sources, "$.must")
    rest, b = C.keep_items(parts["rest"], sources, "$.rest")
    wire, c = C.keep_side(parts["wire"], "wire", sources)
    solo, d = C.keep_side(parts["solo"], "solo", sources)
    context, e = C.keep_context(parts["context"], sources)
    return {**parts, "must": must, "rest": rest, "wire": wire, "solo": solo, "context": context}, len(a + b + c + d + e)


def _notes(status, parts, collect, truncated, missing):
    """판 머리의 알림 줄 — 고정 문구만."""
    n, kr10 = len(parts["must"]), parts["head"]["kr10"]
    out = [R.phrase("note_short")] if status == "short" else [R.phrase("note_none")] if n == 0 else \
        [R.phrase("note_fewer", n=n)] if n < TH["must_max"] else []
    out += [R.phrase("note_no_rates")] if kr10 is None else [] if kr10["fits"] else [R.phrase("note_prev_close")]
    out += [R.phrase("note_capped")] if collect["capped"] else []
    out += [R.phrase("note_rerun")] if collect["window_kind"] == "rerun" else []
    out += [R.phrase("note_truncated", n=truncated)] if truncated else []
    return out + ([R.phrase("note_channels", n=missing)] if missing else [])


def _doc(scored, collect, parts, cut):
    """재료 → 판. 나머지 표는 점수순 재료의 뒤에서 cut줄을 줄이고 8칸 순서로 묶는다."""
    health, cs = S.coverage_verdict(collect["channels"]), scored["clusters"]
    status = "short" if health["verdict"] == "short" else "ok"
    kept = parts["rest"][:len(parts["rest"]) - cut]
    groups = [{"cell": k, "items": [x for x in kept if R.cell_id(**x["cell"]) == k]} for k in R.CELLS]
    funnel = {"posts": scored["stats"]["posts"], "clusters": sum(any(m["role"] == "source" for m in c["members"]) for c in cs),
              "candidates": sum(c["gate"]["pass"] for c in cs), "must": len(parts["must"]), "truncated": cut}
    missing = health["channels_total"] - health["channels_ok"]
    return {"schema": S.SCHEMA, "date": scored["edition"], "mode": "rules", "status": status, "window": dict(scored["window"]),
            "collected_at": scored["collected_at"], "funnel": funnel,
            "sources": {"channels_ok": health["channels_ok"], "channels_total": health["channels_total"]},
            "head": parts["head"], "notes": _notes(status, parts, collect, cut, missing), "must": parts["must"],
            "rest": [g for g in groups if g["items"]], "wire": parts["wire"], "solo": parts["solo"], "context": parts["context"],
            "tomorrow": parts["tomorrow"], "youtube": {"enabled": False, "rows": []}}


def edition(scored, collect, sources, overrides):
    """공개 판 하나 → (판, {항목 id: 묶음}, 검사에서 뺀 것의 수). 크기 상한에 맞을 때까지 나머지 표를 점수가 낮은 줄부터 줄인다."""
    parts, trace = _parts(scored, collect, sources, overrides)
    parts, dropped = _guard(parts, sources)
    cut = max(0, len(parts["rest"]) - TH["rest_max"])
    while True:
        d = _doc(scored, collect, parts, cut)
        if len(S.dump(d).encode("utf-8")) <= C.EDITION_BYTES:
            return d, trace, dropped
        if cut >= len(parts["rest"]):
            raise ValueError("나머지 표를 다 줄여도 판이 크기 상한을 넘음")
        cut += 1


def _withdrawn(scored):
    """숨김 파일이 판 전체를 내리라고 한 날 — 빈 판. 창과 수집 시각은 그대로 둬서 다음 판의 창이 여기서 이어지게 한다."""
    blank = S.blank_digest(S.parse_iso(scored["window"]["to"]))
    return {**blank, "window": dict(scored["window"]), "collected_at": scored["collected_at"]}


# ---------- 상태 기록 · 목차 · 갱신 상태 ----------

def _snap(d, trace, collect, base):
    """이번 판의 기록(숫자·해시만). 못 읽은 채널은 직전 판의 마지막 글 번호·시각을 이어 쓴다(다음 수집이 어디까지 읽었는지 잊지 않게)."""
    old, chans = (base or {}).get("channels", {}), {}
    for c in collect["channels"]:
        prev = old.get(c["ch"], {}) if c["last_post"] is None else c
        chans[c["ch"]] = {"last_post": prev.get("last_post"), "last_at": prev.get("last_at"), "fail_streak": c["fail_streak"]}
    bond_new = sum(c["in_window"] for c in collect["channels"] if c["ok"] and c["group"] == "bond")
    streak = C.next_streak(d["status"], len(d["must"]), bond_new, base["empty_streak"] if base else 0)
    must = [{"id": x["id"], "keys": list(trace[x["id"]]["keys"]), "c": trace[x["id"]]["score"]["C"]} for x in d["must"]]
    before = (base.get("read_to") or base["window"]["to"]) if base else d["window"]["from"]
    return {"date": d["date"], "window": dict(d["window"]), "collected_at": d["collected_at"], "empty_streak": streak,
            "must": must, "channels": chans, "read_to": before if d["status"] == "short" else d["window"]["to"]}


def _trim(snap, handles):
    """판의 기록에서 지금 목록에 없는 채널의 것을 뺀다 — 목록에서 뺀 채널이 다음 날의 닫힌 글자 검사를 막지 않게."""
    if snap is None:
        return None
    return {**snap, "channels": {k: v for k, v in snap["channels"].items() if k in handles},
            "must": [m for m in snap["must"] if S.ID_RE.fullmatch(m["id"]).group("ch") in handles]}


def _index(index, row, at):
    """목차 — 이번 판을 넣고(같은 날짜는 바꿔 넣는다) 최신순, keep_days일 안의 것만."""
    floor = (datetime.date.fromisoformat(row["date"]) - datetime.timedelta(days=TH["keep_days"])).isoformat()
    rows = [row] + [dict(e) for e in (index or {}).get("editions", []) if e["date"] != row["date"] and e["date"] > floor]
    rows.sort(key=lambda e: e["date"], reverse=True)
    return {"schema": S.SCHEMA, "updated_at": at, "latest": rows[0]["date"], "editions": rows}


def _status(at, reason, date, published, collect, index, streak):
    """갱신 상태. 마지막 정상 판은 목차에서 찾는다(이번 판이 정상이면 이번 판)."""
    health = S.coverage_verdict(collect["channels"] if collect else [])
    good = next((e for e in (index or {}).get("editions", []) if e["status"] == "ok"), None)
    return {"schema": S.SCHEMA, "checked_at": at, "ok": reason == "ok", "reason": reason, "edition": date, "published": published,
            "last_success": {"date": good["date"], "at": good["collected_at"]} if good else None, "empty_streak": streak,
            "counts": {k: health[k] for k in C.COUNT_KEYS},
            "channels": [{k: c[k] for k in C.CHAN_KEYS} for c in collect["channels"]] if collect else [],
            "expect": {"run_kst": TH["run_kst"], "late_kst": TH["late_kst"]}}


def _streak_now(state):
    return state["edition"]["empty_streak"] if state["edition"] else 0


def assemble(scored, collect, state, index, overrides, sources):
    """검증된 입력 → (종료코드, {파일 이름: 자료}, {dropped, changed, stale}). 입력은 고치지 않는다."""
    same = ("edition", "window", "collected_at")
    if [scored[k] for k in same] != [collect[k] for k in same]:
        raise ValueError("점수 자료와 수집 기록이 같은 실행의 것이 아님")
    date, at = scored["edition"], scored["collected_at"]
    changed = sum(c["code"] in CHANGED for c in collect["channels"])
    stale = sum(c["group"] == "bond" and c["fail_streak"] >= TH["fail_streak_alert"] for c in collect["channels"])
    if collect["verdict"] == "broken":
        status = _status(at, "broken", date, False, collect, index, _streak_now(state))
        return 3, {"digest_status.json": status}, {"dropped": 0, "changed": changed, "stale": stale}
    d, trace, dropped = (_withdrawn(scored), {}, 0) if overrides["withdraw"] else edition(scored, collect, sources, overrides)
    snap = _snap(d, trace, collect, S.state_base(state, date))
    moved, new_index = S.next_state(state, snap), _index(index, C.index_row(d), at)
    new_state = {**moved, "base": _trim(moved["base"], S.handles_of(sources))}
    flagged = d["status"] == "ok" and snap["empty_streak"] >= TH["empty_streak_fail"]
    reason = "empty_streak" if flagged else d["status"]
    files = {"digest.json": d, f"digest/{date}.json": d, "digest_index.json": new_index, "digest_state.json": new_state,
             "digest_status.json": _status(at, reason, date, True, collect, new_index, snap["empty_streak"])}
    alert = reason in ("short", "empty_streak") or changed or stale
    return (2 if alert else 0), files, {"dropped": dropped, "changed": changed, "stale": stale}


def blank(now, state, handles):
    """내리기 전용 → {파일 이름: 자료}. 빈 판, 이 판만 든 목차, 꼭 볼 것의 id를 지운 상태 기록(창과 채널별 글 번호는 남긴다)."""
    d = S.blank_digest(now)
    date, at = d["date"], d["collected_at"]
    clean = {k: (None if state[k] is None else {**_trim(state[k], handles), "must": []}) for k in ("edition", "base")}
    index = {"schema": S.SCHEMA, "updated_at": at, "latest": date, "editions": [C.index_row(d)]}
    return {"digest.json": d, f"digest/{date}.json": d, "digest_index.json": index, "digest_state.json": {"schema": S.SCHEMA, **clean},
            "digest_status.json": _status(at, "withdrawn", date, True, None, index, _streak_now(state))}


def failed(now, state, index, collect):
    """실행이 실패한 날 → 상태 파일 하나(reason error, 판은 내지 않음). 수집까지는 됐으면 건강 숫자를 싣는다."""
    date = S.edition_date(now)
    seen = collect if collect and collect["edition"] == date else None
    return {"digest_status.json": _status(S.iso(now), "error", date, False, seen, index, _streak_now(state))}


# ---------- 읽고 쓰기 · 실행 ----------

def _soft(read, default=None):
    """내리기·실패 기록은 깨진 입력에 막히면 안 된다 — 못 읽으면 default."""
    try:
        return read()
    except (OSError, ValueError, KeyError, TypeError):
        return default


def _read(folder, name, default=...):
    """파일 하나를 읽고 계약대로 검증한다(경계). default를 주면 파일이 없을 때 그것."""
    doc = S.read_json(os.path.join(folder, name), default)
    return doc if doc is None else S.validator_for(name)(doc)


def write(out, files, sources, wipe=False):
    """전부 검사한 뒤에 쓴다 — 하나라도 어긋나면 아무것도 쓰지 않는다. wipe면 <out>/digest/의 다른 날짜 판을 지운다(내리기)."""
    for name, doc in files.items():
        day = name.startswith("digest/") or name == "digest.json"
        if sources is None:
            S.validator_for(name)(doc)
        elif C.check_edition(doc, sources, name) if day else C.check_file(name, doc, sources):
            raise ValueError("검사에 걸린 산출물은 쓰지 않음")
    for name in sorted(files, key=lambda n: ORDER.index(n) if n in ORDER else -1):
        S.write_json(os.path.join(out, *name.split("/")), files[name])
    sub = os.path.join(out, "digest")
    for n in sorted(os.listdir(sub)) if wipe and os.path.isdir(sub) else []:
        if C.DAY_FILE.fullmatch(n) and f"digest/{n}" not in files:
            os.remove(os.path.join(sub, n))


def _takedown(a, data, work, now):
    """--blank · --error — 사람이 고치다 깨뜨렸을 수 있는 파일에 기대지 않는다."""
    sources = _soft(lambda: _read(data, "sources.json"))
    handles = S.handles_of(sources) if sources else set()
    state = _soft(lambda: _read(data, "digest_state.json", EMPTY_STATE), EMPTY_STATE) if sources else EMPTY_STATE
    if a.blank:
        return 0, blank(now, state, handles), sources
    index = _soft(lambda: _read(data, "digest_index.json", None))
    collect = _soft(lambda: _read(work, "collect_status.json"))
    known = collect and all(c["ch"] in handles for c in collect["channels"])
    return 0, failed(now, state, index, collect if known else None), sources


def _normal(data, work):
    sources = _read(data, "sources.json")
    scored, collect = _read(work, "scored.json"), _read(work, "collect_status.json")
    state, index = _read(data, "digest_state.json", EMPTY_STATE), _read(data, "digest_index.json", None)
    code, files, facts = assemble(scored, collect, state, index, _read(data, "digest_overrides.json", EMPTY_OVERRIDES), sources)
    return code, files, sources, facts


def main(argv=None):
    ap = argparse.ArgumentParser(description="저녁판 조립 — scored.json → 공개 JSON(digest · digest/<날짜> · index · state · status)")
    ap.add_argument("--work", default=S.WORK, help="작업 폴더 — scored.json · collect_status.json (기본: .work/evening)")
    ap.add_argument("--out", required=True, help="쓸 폴더")
    ap.add_argument("--data", default=S.DATA, help="지난 상태·목차·숨김·출처 목록을 읽을 폴더 (기본: 저장소의 data/)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--blank", action="store_true", help="내리기 전용: 빈 판을 쓰고 지난 판 파일과 목차를 지운다")
    mode.add_argument("--error", action="store_true", help="실행이 실패한 날: 상태(reason error)만 쓴다")
    ap.add_argument("--now", default=None, help="--blank · --error의 기준 시각(ISO +09:00, 기본: 지금)")
    a = ap.parse_args(argv)
    out, data, work = (os.path.abspath(p) for p in (a.out, a.data, a.work))
    facts = {}
    if a.blank or a.error:
        now = S.parse_iso(a.now) if a.now else datetime.datetime.now(S.KST)
        code, files, sources = _takedown(a, data, work, now)
    else:
        code, files, sources, facts = _normal(data, work)
    write(out, files, sources, wipe=a.blank)
    d, status = files.get("digest.json"), files["digest_status.json"]
    shown = {"edition": status["edition"], **({"status": d["status"]} if d else {}), "reason": status["reason"]}
    if d:
        shown.update(must=len(d["must"]), rest=sum(len(g["items"]) for g in d["rest"]), wire=len(d["wire"]["rows"]),
                     solo=len(d["solo"]["rows"]), truncated=d["funnel"]["truncated"], dropped=facts.get("dropped", 0),
                     bytes=len(S.dump(d).encode("utf-8")))
    S.report("digest_build", **shown, **{k: facts[k] for k in ("changed", "stale") if facts.get(k)}, code=code)
    return code


if __name__ == "__main__":
    sys.exit(S.run_cli("digest_build", main))
