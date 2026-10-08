#!/usr/bin/env python3
"""저녁판 점수 — 묶음마다 S = C + X + K + E + M + Y − P를 매기고 꼭 볼 것 3건과 나머지 표를 고른다 (2026-10-08, 1단계 규칙 선별판).

<work>/clusters.json(닫힌 값만) + calendar.json(일정) + korea.json(아침 잡의 금리·국고채 입찰 일정) + digest_state.json(직전 판)
→ <work>/scored.json. 원문은 보지 않는다 — 볼 길이 없다. 숫자는 전부 digest_rules.TH에서 읽는다(검증 전 제안값).
규칙은 방향·강도를 내지 않는다. 머리 줄의 낱말도 원인이 아니라 '가장 많이 다뤄진 주제'일 뿐이다.

점수 (설계 4절 + 12절)
  C 다룬 곳   그룹마다 첫 채널 w, 둘째부터 w_next·w, 그룹 합은 w_group_cap·w까지(w = 채권 2.0 · 애널 1.0 · 개인 0.5). 직접 쓴 채널이
              앞자리를 차지하고 전달로만 참여한 채널은 뒤에서 절반. 속보형은 원천 글이 있는 묶음에 붙었을 때만, 몇 곳이든 +w_wire.
              주제 한정 채널은 원천 글 첫머리에 AI 꼬리표 낱말이 있는 묶음에서만 제 그룹의 채널로 센다.
  X 그룹 확인 채권 + 다른 그룹 1곳 +x_bond_plus, 세 그룹 모두면 +x_all 더.
  K 낱말      묶음의 낱말(첫머리 것만 실려 있다) 가운데 가장 높은 등급 하나. A급은 그 낱말의 일정이 수집 창 안일 때만 A 점수이고
              밖이면 B 점수. 같은 결과 낱말(R.RESULT_K)을 k_result_min_ch곳 이상이 직접 썼으면 +k_result.
  E 일정      묶음의 낱말과 맞는 일정이 수집 창 안에 있으면 A +2.0 · B +1.0. 달력의 일정은 S.in_window, 국고채 입찰(korea.json,
              시각 없음)은 그날 장 마감이 창 안일 때 — 어제 입찰이 오늘 묶음에 다시 가산되지 않게.
  M 금리 변동 채권 채널이 있고 금리 꼬리표 낱말이 있는 묶음에만. 국내 칸은 국고 10년, 글로벌 칸은 미 10년의 최근 일간 변화(절대값)가
              최근 m_obs관측일의 상위 25%면 +1.0, 상위 10%면 +1.5(= 위에서 15번째·6번째로 큰 변화 이상). 금리의 자료일이
              수집 창과 맞지 않으면(S.rate_fits) 0이고, 이유는 head의 fits·basis(전일 종가)에 남는다.
  Y · L       1단계에서는 0 · null.
  P 감점      직전 판의 꼭 볼 것과 열쇠가 겹치면 p_repeat(C가 p_repeat_waive_c 이상 늘면 면제) · 센 채널의 절반 넘게 전달뿐이면 p_fwd ·
              C급 낱말뿐이고 기타 칸이면 p_c_only_etc. 직전 판은 S.state_base가 고른다(같은 판을 다시 돌아도 '어제'는 그대로).
게이트(전부 통과해야 후보): sources 원천 gate_sources곳 이상(예외: 채권 1곳 + E gate_bond_alone_e) · grade A·B급 낱말 · score S gate_s
  이상 · group 채권이나 애널 1곳 이상.
고르기: 후보를 점수순(같으면 이른 묶음)으로 must_max건까지, 같은 칸은 cell_max건까지, 통과한 국내 묶음이 있으면 must_domestic_min건은
  국내. 모자라면 그만큼만. 나머지 표(rest) = 원천 rest_sources곳 이상, 또는 채권·애널 원천이 낀 S rest_s 이상, 또는 채권 채널의 글
  (단독 글도 전부). 30줄 상한은 조립 단계가 건다. 개인·속보형이 혼자 쓴 글은 none — 조립 단계가 solo·wire 절의 줄로 쓴다.

사용법: python scripts/evening/digest_score.py [--work .work/evening] [--calendar data/calendar.json] [--korea data/korea.json]
        [--state data/digest_state.json]
"""
import argparse
import datetime
import math
import os
import sys

import digest_cluster as DC
import digest_rules as R
import digest_schema as S

TH = S.TH
AB = ("A", "B")
RATE_KEYS = ("kr10", "kr3", "us10")          # korea.json 카드의 key — 앞 두 글자가 마감 시각 표(TH close_kst)의 이름이다
ETC = "기타"


# ---------- 일정 ----------

def event_in(window, e):
    """일정이 수집 창과 맞는가. 달력의 일정은 S.in_window, 국고채 입찰(korea.json)은 그날 장 마감이 창 안일 때."""
    return S.rate_fits("kr", e["date"], window) if e["src"] == "korea" else S.in_window(window, e["date"], e["time"])


def tomorrow_of(events, window):
    """내일 볼 것 — 창이 끝난 뒤 tomorrow_days일 안의 일정을 날짜·시각순으로 tomorrow_max개까지. 오늘 밤 일정도 여기에 든다."""
    to = S.parse_iso(window["to"])
    last = (to.date() + datetime.timedelta(days=TH["tomorrow_days"])).isoformat()

    def ahead(e):
        when = S.parse_iso(f"{e['date']}T{e['time'] or '23:59'}:00+09:00")
        return when > to and e["date"] <= last and not event_in(window, e)
    return [{**e, "detail": list(e["detail"])} for e in events if ahead(e)][:TH["tomorrow_max"]]


# ---------- 금리 (korea.json — 아침 잡의 것을 읽기만 한다) ----------

def _points(korea, key):
    """카드 하나의 [날짜, 값] 줄들. 꼴이 하나라도 다르면 빈 목록(닫힌 쪽으로)."""
    cards = korea.get("cards") if isinstance(korea, dict) else None
    card = next((c for c in cards if isinstance(c, dict) and c.get("key") == key), None) if isinstance(cards, list) else None
    pts = card.get("points") if card else None
    if not isinstance(pts, list):
        return []
    ok = all(type(p) is list and len(p) == 2 and isinstance(p[0], str) and S.DATE_RE.fullmatch(p[0])
             and type(p[1]) in (int, float) and math.isfinite(p[1]) for p in pts)
    return pts if ok and [p[0] for p in pts] == sorted({p[0] for p in pts}) else []


def _move_bonus(pts):
    """최근 일간 변화(절대값)가 최근 m_obs관측일 가운데 상위 10%·25%에 드는가 → 가산. 관측일이 모자라면 0."""
    n = TH["m_obs"]
    if len(pts) < n + 1:
        return 0
    moves = [round(abs(b[1] - a[1]) * 100, 6) for a, b in zip(pts[-n - 1:], pts[-n:])]
    ranked = sorted(moves)
    for q, bonus in TH["m_steps"]:
        if moves[-1] > 0 and moves[-1] >= ranked[n - max(1, round((1 - q) * n))]:
            return bonus
    return 0


def read_rate(korea, key, window):
    """korea.json의 금리 카드 하나 → {"value", "chg_bp", "asof", "fits", "bonus"} 또는 None(없음·꼴이 다름·범위 밖).
    fits = 자료일의 마감이 수집 창 안, bonus = 변동 가산(자료일이 안 맞으면 0)."""
    pts = _points(korea, key)
    if len(pts) < 2 or not TH["rate_min"] < pts[-1][1] < TH["rate_max"]:
        return None
    try:
        fits = S.rate_fits(key[:2], pts[-1][0], window)
    except ValueError:                                     # 없는 날짜
        return None
    chg = round((pts[-1][1] - pts[-2][1]) * 100, 2)
    return {"value": round(pts[-1][1], 3), "chg_bp": chg if abs(chg) <= TH["chg_bp_max"] else None, "asof": pts[-1][0], "fits": fits,
            "bonus": min(_move_bonus(pts), TH["m_cap"]) if fits else 0}


def _side(x, names):
    """변화(bp) → 방향 이름. ±head_flat_bp 안이면 names[2](보합), 밖이면 오른 쪽 names[0] · 내린 쪽 names[1]."""
    x = round(x, 6)
    return names[2] if abs(x) <= TH["head_flat_bp"] else names[0] if x > 0 else names[1]


def head_of(rates, top_terms):
    """판 머리의 금리 줄. 국고 10년의 자료일이 창과 안 맞으면 방향을, 10년·3년 중 하나라도 안 맞으면 커브를 비운다."""
    kr10, kr3 = rates["kr10"], rates["kr3"]
    ok10 = bool(kr10 and kr10["fits"] and kr10["chg_bp"] is not None)
    ok3 = bool(ok10 and kr3 and kr3["fits"] and kr3["chg_bp"] is not None and kr3["asof"] == kr10["asof"])
    out = {k: rates[k] and {f: rates[k][f] for f in ("value", "chg_bp", "asof", "fits")} for k in RATE_KEYS}
    return {**out, "dir": _side(kr10["chg_bp"], R.DIRS) if ok10 else None,                 # 금리가 오르면 약세
            "curve": _side(kr10["chg_bp"] - kr3["chg_bp"], R.CURVES) if ok3 else None,     # 10년−3년이 벌어지면 스팁
            "basis": kr10 and R.BASES[0 if kr10["fits"] else 1], "top_terms": top_terms}


# ---------- 점수의 항 ----------

def counted(c):
    """점수에 세는 글 — 원천 채널의 글과, 원천 글 첫머리에 AI 꼬리표 낱말이 있는 묶음의 주제 한정 채널 글."""
    src = [m for m in c["members"] if m["role"] == "source"]
    ai = R.has_tag([t for m in src for t in m["lead"]], R.TOPIC_TAG)
    return src + [m for m in c["members"] if m["role"] == "topic" and ai]


def coverage(c):
    """그룹별로 센 채널 수 + 속보형 채널 수."""
    got = {g: set() for g in R.GROUPS}
    for m in counted(c):
        got[m["group"]].add(m["ch"])
    return {**{g: len(v) for g, v in got.items()}, "wire": len({m["ch"] for m in c["members"] if m["role"] == "wire"})}


def c_score(c):
    """C 다룬 곳."""
    only_fwd = {}                                          # (그룹, 채널) → 전달로만 참여했는가
    for m in counted(c):
        only_fwd[(m["group"], m["ch"])] = only_fwd.get((m["group"], m["ch"]), True) and m["fwd"]
    total = 0.0
    for g, w in TH["w"].items():
        flags = sorted(f for (group, _), f in only_fwd.items() if group == g)          # 직접 쓴 채널이 앞자리
        part = sum(w * (1 if i == 0 else TH["w_next"]) * (TH["w_fwd_only"] if f else 1) for i, f in enumerate(flags))
        total += min(part, w * TH["w_group_cap"])
    roles = {m["role"] for m in c["members"]}
    return round(min(total + (TH["w_wire"] if {"wire", "source"} <= roles else 0), TH["c_cap"]), 3)


def x_score(cov):
    """X 그룹 넘은 확인."""
    others = (cov["analyst"] > 0) + (cov["personal"] > 0)
    if not (cov["bond"] and others):
        return 0
    return min(TH["x_bond_plus"] + (TH["x_all"] if others == 2 else 0), TH["x_cap"])


def same_result(c):
    """같은 결과 낱말(K에 세는 것만)을 쓴 채널 수 가운데 가장 큰 것."""
    return max((r["n_ch"] for r in c["results"] if r["result"] in R.RESULT_K), default=0)


def k_score(c, hot):
    """K 낱말. hot = 수집 창 안에 일정이 있는 낱말들."""
    def worth(term):
        grade = R.grade_of(term)
        return TH["k"]["B" if grade == "A" and term not in hot else grade]
    base = max((worth(t["term"]) for t in c["terms"]), default=0)
    bonus = TH["k_result"] if base and same_result(c) >= TH["k_result_min_ch"] else 0
    return min(base + bonus, TH["k_cap"])


def e_event(c, inside):
    """E 일정 → (점수, 맞은 일정 또는 None). 묶음의 낱말과 맞는 창 안 일정 가운데 등급이 가장 높은 것."""
    names = {t["term"] for t in c["terms"]}
    best = min((e for e in inside if e["term"] in names), key=lambda e: (e["tier"], e["src"]), default=None)
    return (min(TH["e"][best["tier"]], TH["e_cap"]), best) if best else (0, None)


def m_score(c, cov, rates):
    """M 금리 변동."""
    if not (c["cell"] and cov["bond"] and R.has_tag([t["term"] for t in c["terms"]], R.RATE_TAG)):
        return 0
    rate = rates["kr10" if c["cell"]["region"] == "국내" else "us10"]
    return rate["bonus"] if rate else 0


def p_flags(c, c_now, base):
    """감점 사유 → {"repeat", "fwd", "etc"}."""
    chans = {m["ch"] for m in counted(c)}
    direct = {m["ch"] for m in counted(c) if not m["fwd"]}
    before = [x["c"] for x in (base or {}).get("must", []) if set(x["keys"]) & set(c["keys"])]
    grade = R.best_grade([t["term"] for t in c["terms"]])
    return {"repeat": bool(before) and c_now - max(before) < TH["p_repeat_waive_c"],
            "fwd": len(chans - direct) > TH["p_fwd_share"] * len(chans),
            "etc": grade == "C" and c["cell"]["factor"] == ETC}        # 낱말이 있으면 칸도 있다(계약)


def gate_of(c, cov, total, e):
    """게이트 → ({"pass", "fails"}, 채권 1곳 + 일정 예외로 통과했는가)."""
    sources = len({m["ch"] for m in c["members"] if m["role"] == "source"})
    few = sources < TH["gate_sources"]
    alone = few and cov["bond"] >= 1 and e >= TH["gate_bond_alone_e"]
    bad = {"sources": few and not alone, "grade": R.best_grade([t["term"] for t in c["terms"]]) not in AB,
           "score": total < TH["gate_s"], "group": not (cov["bond"] or cov["analyst"])}
    fails = [code for code in S.GATE_CODES if bad[code]]
    return {"pass": not fails, "fails": fails}, alone


def why_of(c, cov, s, flags, event, alone):
    """이유 칩(고정 문구) — 다룬 곳 → 그룹 확인 → 일정 → 감점 → 금리 → 숫자 → 결과 낱말 → 등급 → 속보형 순으로 why_max개까지."""
    out, lead = [], next((g for g in R.GROUP_ORDER if cov[g]), None)
    if lead:
        out.append(R.phrase(f"why_{lead}", n=cov[lead]))
    if s["X"]:
        out.append(R.phrase("why_all" if s["X"] > TH["x_bond_plus"] else "why_cross"))
    if event:
        out.append(R.phrase("why_bond_alone" if alone else "why_auction" if event["src"] == "korea" else "why_event"))
    out += [R.phrase(code) for code, on in (("why_repeat", flags["repeat"]), ("why_fwd", flags["fwd"]), ("why_move", s["M"])) if on]
    if c["nums"]:
        out.append(R.phrase("why_num", n=max(n["n_ch"] for n in c["nums"])))
    if same_result(c) >= TH["k_result_min_ch"]:
        out.append(R.phrase("why_result", n=same_result(c)))
    if s["K"] >= TH["k"]["A"]:
        out.append(R.phrase("why_grade_a"))
    if lead and cov["wire"]:
        out.append(R.phrase("why_wire"))
    return out[:TH["why_max"]]


def score_cluster(c, ctx):
    """묶음 하나에 다룬 곳·점수·게이트·이유를 붙인다(고르기 전 — pick none, rank null). ctx = {inside, hot, rates, base}."""
    cov = coverage(c)
    e, event = e_event(c, ctx["inside"])
    s = {"C": c_score(c), "X": x_score(cov), "K": k_score(c, ctx["hot"]), "E": e, "M": m_score(c, cov, ctx["rates"]), "Y": 0}
    flags = p_flags(c, s["C"], ctx["base"])
    p = min(sum(TH[k] for k, on in (("p_repeat", flags["repeat"]), ("p_fwd", flags["fwd"]), ("p_c_only_etc", flags["etc"])) if on),
            TH["p_cap"])
    total = round(s["C"] + s["X"] + s["K"] + s["E"] + s["M"] + s["Y"] - p, 3)
    gate, alone = gate_of(c, cov, total, e)
    score = {"total": total, **s, "P": p, "L": None}
    return {**c, "coverage": cov, "score": score, "gate": gate, "why": why_of(c, cov, score, flags, event, alone), "pick": "none",
            "rank": None}


# ---------- 고르기 ----------

def _order(c):
    return (-c["score"]["total"], c["first_at"], c["seed"]["ch"], c["seed"]["id"])


def _fill(scored, passed, first):
    """점수순 후보에서 must_max건까지 — 같은 칸은 cell_max건까지. first는 먼저 넣어 둘 것."""
    chosen = list(first)
    for i in passed:
        same = sum(R.cell_id(**scored[j]["cell"]) == R.cell_id(**scored[i]["cell"]) for j in chosen)
        if len(chosen) < TH["must_max"] and i not in chosen and same < TH["cell_max"]:
            chosen.append(i)
    return chosen


def in_rest(c):
    """나머지 표에 드는가 — 원천 rest_sources곳 이상, 또는 채권·애널 원천이 낀 S rest_s 이상, 또는 채권 채널의 글(단독 글도 전부)."""
    src = {(m["group"], m["ch"]) for m in c["members"] if m["role"] == "source"}
    groups = {g for g, _ in src}
    strong = c["score"]["total"] >= TH["rest_s"] and any(g in groups for g in TH["rest_s_groups"])
    return len(src) >= TH["rest_sources"] or strong or "bond" in groups


def choose(scored):
    """꼭 볼 것과 나머지 표를 고른 새 목록. 통과한 국내 묶음이 있는데 점수순 3건에 없으면 가장 높은 국내 묶음을 먼저 넣고 채운다."""
    order = sorted(range(len(scored)), key=lambda i: _order(scored[i]))
    passed = [i for i in order if scored[i]["gate"]["pass"] and scored[i]["terms"]]
    must = _fill(scored, passed, [])
    home = [i for i in passed if scored[i]["cell"]["region"] == "국내"]
    if sum(i in home for i in must) < min(TH["must_domestic_min"], len(home)):
        must = _fill(scored, passed, home[:TH["must_domestic_min"]])
    rank = {i: n + 1 for n, i in enumerate(sorted(must, key=order.index))}
    return [{**c, "pick": "must" if i in rank else "rest" if in_rest(c) else "none", "rank": rank.get(i)} for i, c in enumerate(scored)]


def top_terms(scored):
    """가장 많이 다뤄진 주제 — 원천 채널이 첫머리에 직접 쓴(전달 제외) A·B급 낱말을 채널 수로 센다. rest_sources곳 이상이 쓴 낱말을
    많이 쓴 순(같으면 그룹 가중의 합 · 등급 · 가나다)으로 top_terms_max개까지. 묶음의 대표 낱말이 아니라 글에서 세므로 묶기가 틀려도
    흔들리지 않는다."""
    seen = {}
    for c in scored:
        for m in c["members"]:
            if m["role"] == "source" and not m["fwd"]:
                for t in m["lead"]:
                    if R.grade_of(t) in AB:
                        seen.setdefault(t, {})[m["ch"]] = TH["w"][m["group"]]
    wide = [(-len(chs), -sum(chs.values()), R.GRADES.index(R.grade_of(t)), t) for t, chs in seen.items() if len(chs) >= TH["rest_sources"]]
    return [row[-1] for row in sorted(wide)][:TH["top_terms_max"]]


# ---------- 문서 ----------

def score_doc(clusters, calendar, korea, state):
    """clusters.json의 자료 + 일정 + 금리 + 직전 판 상태 → scored.json의 자료. 입력은 고치지 않는다."""
    window, events = clusters["window"], DC.events_of(calendar, korea)
    inside = [e for e in events if event_in(window, e)]
    rates = {k: read_rate(korea, k, window) for k in RATE_KEYS}
    ctx = {"inside": inside, "hot": {e["term"] for e in inside}, "rates": rates, "base": S.state_base(state, clusters["edition"])}
    scored = choose([score_cluster(c, ctx) for c in clusters["clusters"]])
    return {"schema": S.SCHEMA, "edition": clusters["edition"], "window": dict(window), "collected_at": clusters["collected_at"],
            "stats": {**clusters["stats"], "dropped": dict(clusters["stats"]["dropped"])}, "head": head_of(rates, top_terms(scored)),
            "tomorrow": tomorrow_of(events, window), "clusters": scored}


def _read_korea(path):
    """korea.json — 없거나 깨졌으면 None(금리 칸만 비우고 판은 낸다)."""
    try:
        return S.read_json(path, None)
    except ValueError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="저녁판 점수 — clusters.json의 묶음에 점수를 매기고 꼭 볼 것을 골라 scored.json을 쓴다")
    ap.add_argument("--work", default=S.WORK, help="작업 폴더 (기본: .work/evening)")
    ap.add_argument("--calendar", default=os.path.join(S.DATA, "calendar.json"), help="일정표 (없으면 일정 없음)")
    ap.add_argument("--korea", default=os.path.join(S.DATA, "korea.json"), help="아침 잡의 금리·입찰 일정 (읽기만)")
    ap.add_argument("--state", default=os.path.join(S.DATA, "digest_state.json"), help="직전 판의 상태 (없으면 첫 실행)")
    a = ap.parse_args(argv)
    clusters = S.validate_clusters_doc(S.read_json(os.path.join(a.work, "clusters.json")))
    calendar = S.read_json(a.calendar, None)
    state = S.validate_state(S.read_json(a.state, {"schema": S.SCHEMA, "edition": None, "base": None}))
    korea = _read_korea(a.korea)
    out = S.validate_scored_doc(score_doc(clusters, calendar and S.validate_calendar(calendar), korea, state))
    S.write_json(os.path.join(a.work, "scored.json"), out)
    picks = [c["pick"] for c in out["clusters"]]
    S.report("digest_score", clusters=len(picks), candidates=sum(c["gate"]["pass"] for c in out["clusters"]), must=picks.count("must"),
             rest=picks.count("rest"), events=sum(event_in(out["window"], e) for e in DC.events_of(calendar, korea)),
             rates=sum(out["head"][k] is not None for k in RATE_KEYS))
    return 0


if __name__ == "__main__":
    sys.exit(S.run_cli("digest_score", main))
