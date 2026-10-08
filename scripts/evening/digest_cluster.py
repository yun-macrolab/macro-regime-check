#!/usr/bin/env python3
"""저녁판 묶기 — 같은 일을 다룬 글끼리 묶는다 (2026-10-08, 1단계 규칙 선별판). 원문을 읽는 마지막 단계다.

<work>/posts.json(원문) + collect_status.json(채널의 그룹·역할) → <work>/clusters.json. 여기서부터는 닫힌 값만 남는다:
사전 낱말 · 결과 낱말 · 숫자+허용 단위 · 시각 · 채널 이름 · 글 번호 · 해시. 글의 글자는 산출물·로그 어디에도 싣지 않는다
(test_digest_cluster.py가 강제). LLM은 쓰지 않는다 — 열쇠가 같은 글을 합집합 찾기로 묶을 뿐이다.

순서
  1) 먼저 버린다(R.drop_code): 본문도 링크도 없음 · 20자 미만에 링크도 없음 · 광고·모집 · 코인·종목 공시(A·B급 낱말이 없을 때).
     주소뿐인 글(본문이 빈다)은 링크가 있으면 두어 주소·카드 열쇠로 묶일 수 있게 한다.
     한 채널의 글 footer_link_min개 이상에 똑같이 붙은 링크는 꼬리말로 보고 링크로도 열쇠로도 세지 않는다.
  2) 원천 채널이 직접 쓴 글(전달 아님)끼리 묶는다.
       f 전달  전달 원글(채널/번호)이 같다. 글 안에 적힌 t.me 글 주소도 같은 재료다
       u 주소  정규화한 링크가 같다(추적 인자·www.·m. 제거, 네이버 뉴스 oid/aid, 유튜브 영상 ID). 단축 주소는 풀지 않는다
       t 카드  링크 카드 제목(card_title_min자 이상)이 같다 — 제목은 해시로만 남는다
       k 주제  채권·애널만: 첫머리 대표 낱말(A·B급)이 같고(낱말이 지역을 정한다) 이어지는 글 사이가 topic_key_hours 안
       g 지문  글자 5-gram 자카드 jaccard_min 이상 또는 포함도 contain_min 이상 — 서로 다른 채널끼리만
       n 숫자  num_key_hours 안에 같은 A·B급 낱말과 짝지은 같은 숫자 num_key_nums개(시세 수준 제외). 묶음의 씨앗 글끼리 맞을 때만.
               숫자만 같고 짝이 다르면 묶지 않는다 — 긴 글끼리 흔한 숫자(5% · 10%)와 낱말 하나가 우연히 겹친다
  3) 전달 글 → 주제 한정 → 속보형 글을 가장 많이 맞는 묶음 하나에만 붙인다(두 묶음을 잇지 못한다. 맞은 수가 같으면 더 이른 묶음).
     맞는 곳이 없는 전달 글은 전달 원글이 같은 것끼리만 묶는다. 속보형끼리는 묶음을 만들지 못하고, 참고(context) 채널의 글은 늘 혼자다.
  묶음은 cluster_max_posts글까지다 — 넘게 되는 합치기는 하지 않고 남은 글은 따로 묶는다.

정해 둔 것 (계약 digest_schema.py에 맞춘 풀이)
  첫머리   첫 두 줄(빈 줄 제외)과 첫 lead_chars자 가운데 짧은 쪽. 줄을 나누지 않은 글은 첫 lead_chars자. 글의 lead · lead_nums ·
           results는 첫머리의 것만이고, 묶음의 terms도 첫머리 낱말만 센다(긴 글 뒤쪽의 낱말이 주제·점수가 되지 않게).
  분류 칸  채널마다 대표 낱말(첫머리에서 먼저 나온 A·B급 낱말, 없으면 첫 낱말)의 칸 하나 — 과반이 같을 때만 그 칸. 갈리면 '분류 보류'인데
           계약은 낱말이 있는 묶음의 칸을 비울 수 없어 기타 칸으로 보낸다(지역은 과반이 같으면 그 지역, 아니면 글로벌).
  숫자 칸  원천 채널 두 곳 이상이 직접 쓴 글(전달 제외)에서 같은 낱말과 짝지은 같은 숫자만. 짝은 숫자 앞 num_term_chars자 안의
           가장 가까운 A·B급 낱말(R.named_before) — 짝이 없는 숫자는 싣지 않는다(묶음의 대표 낱말에 대신 붙이면 없는 사실이
           만들어진다). 결과 낱말은 숫자 곁 num_result_chars자 안에서 과반이 같이 쓴 것. 시세 수준 숫자
           (R.is_quote, 또는 바로 앞 낱말이 금리 수준 낱말인 %·bp)는 숫자 열쇠와 숫자 칸에서 뺀다.
  줄의 짝  글의 row — 혼자 쓴 글이 속보형·개인 단독 줄이 될 때 싣는 (낱말, 숫자). 첫머리의 첫 숫자 하나만 보고(시세 수준이거나
           R.solo_num_ok가 아니면 다음 숫자로 넘어가지 않는다 — 숫자를 골라 싣는 길을 주지 않게) 그 앞의 가까운 A·B급 낱말과 짝짓는다.
           짝이 없으면 숫자 없는 줄(v null): 첫 두 줄(row_head_chars자까지)의 낱말(head) 가운데 먼저 나온 A·B급 낱말, A·B급이 없으면
           그 글의 낱말이 둘 이상일 때 첫 두 줄의 첫 낱말(C급 낱말 하나뿐인 글은 줄이 되지 않는다). 2026-10-08 첫 판에서 줄이
           0개여서 넓혔다 — 그날 저장분의 개인·속보형 단독 글 49개 가운데 첫머리에 A·B급 낱말이 있는 글이 4개뿐이었고 그마저 곁에
           숫자가 없었다. 사전 낱말이 하나도 없는 글(개인 채널의 종목·산업 글)은 여전히 줄이 되지 않는다 — 건수로만 남는다.
  더 자세히  글마다 길이 구간(size — 글자 수는 남기지 않는다) · 그림이 붙었는가(pic) · 첫 두 줄의 낱말(head)을 남긴다.
           글의 낱말(terms)은 member_terms_max개까지 — 조립 단계가 '함께 나온 낱말'과 '이 글에만 더 있는 낱말'을 여기서 센다.
  열쇠     묶음의 keys = 두 글 이상이 함께 가진 f·u·t·k + 씨앗 글과 맞은 n + (지문으로 닮은 쌍이 있거나 다른 열쇠가 없으면) g 하나.
  일정 열쇠  events를 줄 때만(기본은 꺼 둔다 — 계약의 CLI와 열쇠 종류에 없다): 채권·애널 원천 글의 첫머리에 그 일정의 낱말이 있고
           일정 뒤 num_key_hours 안(시각이 없는 일정은 그날)에 올린 글끼리. 열쇠 종류는 k이고 재료 앞에 "e|"를 붙인다.

사용법: python scripts/evening/digest_cluster.py [--work .work/evening] [--calendar data/calendar.json --korea data/korea.json]
"""
import argparse
import collections
import datetime
import os
import re
import sys
import urllib.parse

import digest_rules as R
import digest_schema as S

TH = S.TH
AB = ("A", "B")
KEY_GROUPS = ("bond", "analyst")        # 주제 열쇠·일정 열쇠를 만드는 그룹
AUCTION_A = ("10년", "30년")            # 국고채 입찰 일정의 등급: 10·30년 A, 그 밖 B (설계 4절 E 항)
AUCTION_TERM = "국고채 입찰"
SHARED_MIN = TH["k_result_min_ch"]      # '두 곳 이상이 똑같이 쓴'의 둘 — 숫자 칸과 그 결과 낱말에 쓴다
MAX_WORDS, MAX_KEYS = 12, 60            # 글·묶음에 싣는 낱말·숫자 수, 묶음의 열쇠 수 — 계약(digest_schema)의 형태 상한과 같다
MAX_TERMS = TH["member_terms_max"]      # 글 하나의 낱말 수(글 전체에서 걸린 것, 자리순)

_TG_HOSTS = ("t.me", "telegram.me")
_TG_POST = re.compile(r"^/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,31})/(\d{1,10})$")
_TUBE_ID = r"[A-Za-z0-9_-]{11}"
_TUBE_PATH = re.compile(rf"^/(?:shorts|live|embed|v)/({_TUBE_ID})$")
_NAVER_PATH = re.compile(r"/article/(?:comment/)?(\d{3})/(\d{6,12})$")
_TRACK = re.compile(r"^(?:utm_.*|fbclid|gclid|dclid|igshid|mc_[ce]id|ref|ref_src|ref_url|si|feature|share|spm|cmpid|sfnsn)$", re.I)
_URL_IN_TEXT = re.compile(r"https?://\S+")


# ---------- 링크 → 열쇠 재료 ----------

def _known_site(host, path, q):
    """주소 꼴이 여럿인 곳은 ID로 맞춘다 — 유튜브 영상 · 네이버 뉴스 기사. 아니면 None."""
    if host == "youtu.be" and re.fullmatch(rf"/{_TUBE_ID}", path):
        return ("u", "youtube:" + path[1:])
    if host in ("youtube.com", "music.youtube.com"):
        m = _TUBE_PATH.match(path)
        vid = m.group(1) if m else (q.get("v", "") if path == "/watch" else "")
        return ("u", "youtube:" + vid) if re.fullmatch(_TUBE_ID, vid) else None
    if host.endswith("news.naver.com"):
        m = _NAVER_PATH.search(path)
        oid, aid = m.groups() if m else (q.get("oid", ""), q.get("aid", ""))
        return ("u", f"naver:{oid}/{aid}") if oid.isdigit() and aid.isdigit() else None
    return None


def norm_link(url):
    """링크 → (열쇠 종류, 재료) 또는 None. 추적 인자 · www. · m. · 끝의 / · # 뒤를 떼고, 유튜브·네이버 뉴스는 ID로 맞춘다.
    t.me 글 주소는 전달 원글과 같은 재료("채널/번호")가 된다. 단축 주소는 풀지 않는다(그 주소가 그대로 재료).
    기사가 아닌 것(사이트·채널의 첫 화면, http가 아닌 주소, 읽을 수 없는 주소)은 None."""
    try:
        u = urllib.parse.urlsplit(url.strip())
        host, query = (u.hostname or "").lower(), urllib.parse.parse_qsl(u.query)
    except (AttributeError, ValueError):
        return None
    if u.scheme not in ("http", "https") or "." not in host:
        return None
    host, path = re.sub(r"^(?:www|m|mobile)\.", "", host), re.sub(r"/+$", "", u.path)
    if host in _TG_HOSTS:
        m = _TG_POST.match(path)
        return ("f", f"{m.group(1).casefold()}/{int(m.group(2))}") if m else None
    known = _known_site(host, path, dict(query))
    keep = sorted((k, v) for k, v in query if not _TRACK.match(k))
    if known or not (path or keep):
        return known
    return ("u", host + path + ("?" + urllib.parse.urlencode(keep) if keep else ""))


def _links(post):
    """글의 링크들 → 정규화한 재료(읽을 수 없는 것은 뺀다). 링크 카드의 주소도 링크다."""
    card = post["card"] or {}
    return {norm_link(u) for u in list(post["links"]) + [card.get("url")]} - {None}


def footer_links(posts):
    """{채널: 꼬리말 링크들} — 한 채널의 글 footer_link_min개 이상에 똑같이 붙은 링크."""
    seen = {p["ch"]: collections.Counter() for p in posts}
    for p in posts:
        seen[p["ch"]].update(_links(p))
    return {ch: {k for k, n in c.items() if n >= TH["footer_link_min"]} for ch, c in seen.items()}


def post_keys(post, footers=()):
    """글의 센 열쇠들(f·u·t). 제 글 번호의 f 열쇠를 늘 가진다 — 이 글을 전달하거나 주소로 가리킨 글과 만나게."""
    mats = {("f", f"{post['ch'].casefold()}/{post['id']}")} | (_links(post) - set(footers))
    origin = fwd_origin(post)
    title = R.norm_text((post["card"] or {}).get("title")).casefold()
    if len(title) >= TH["card_title_min"]:
        mats.add(("t", title))
    return {S.key_of(kind, m) for kind, m in mats} | ({origin} if origin else set())


def fwd_origin(post):
    """전달 원글의 f 열쇠. 전달이 아니거나 원글 주소를 모르면 None."""
    fwd = post["fwd"]
    return S.key_of("f", f"{fwd['ch'].casefold()}/{fwd['id']}") if fwd and fwd["ch"] and fwd["id"] else None


# ---------- 글 하나 → 닫힌 값 ----------

def lead_end(text):
    """첫머리가 끝나는 자리(R.norm_text 좌표) — 첫 두 줄(빈 줄은 세지 않는다)과 첫 lead_chars자 가운데 짧은 쪽.
    줄을 나누지 않았거나 두 줄뿐인 글은 첫 lead_chars자."""
    lines = [x for x in map(R.norm_text, (text or "").splitlines()) if x]
    return min(len(" ".join(lines[:2])), TH["lead_chars"]) if len(lines) > 2 else TH["lead_chars"]


def head_end(text):
    """단독 줄이 보는 첫머리가 끝나는 자리(R.norm_text 좌표) — 첫 두 줄(빈 줄은 세지 않는다), row_head_chars자까지.
    lead_end보다 앞서지 않는다(첫머리 낱말은 늘 이 안에 있다)."""
    lines = [x for x in map(R.norm_text, (text or "").splitlines()) if x]
    return max(min(len(" ".join(lines[:2])), TH["row_head_chars"]), min(lead_end(text), len(R.norm_text(text))))


def scan(text):
    """글을 한 번 훑는다 → 낱말·결과 낱말·숫자(자리와 함께), 낱말의 자리 전부(hits), 첫머리의 끝(end), 첫 두 줄의 끝(head).
    같은 글을 여러 번 훑지 않게 mention · num_pairs에 넘긴다."""
    return {"terms": R.match_terms(text), "results": R.match_results(text), "nums": R.find_nums(text), "hits": R.term_hits(text),
            "end": lead_end(text), "head": head_end(text)}


def mention(post, group, role, found=None, pairs=None):
    """글 하나에서 닫힌 값만 남긴다 — 낱말·숫자와 그 가운데 첫머리에 있는 것, 첫머리의 결과 낱말, 줄의 짝. 원문은 여기서 끝난다."""
    found = found or scan(post["text"])
    terms, nums, end = found["terms"][:MAX_TERMS], found["nums"][:MAX_WORDS], found["end"]
    lead = [t["term"] for t in terms if t["pos"] < end][:MAX_WORDS]
    m = {"ch": post["ch"], "id": post["id"], "at": post["at"], "group": group, "role": role, "fwd": post["fwd"] is not None,
         "terms": [t["term"] for t in terms], "lead": lead,
         "results": [r["result"] for r in found["results"] if r["pos"] < end],
         "nums": [n["v"] for n in nums], "lead_nums": [n["v"] for n in nums if n["pos"] < end],
         "size": R.size_of(post["text"]), "pic": bool(post.get("pic")),
         "head": [t["term"] for t in terms if t["pos"] < found.get("head", end) or t["term"] in lead]}
    return {**m, "row": row_pair(m, found, num_pairs(post["text"], found) if pairs is None else pairs)}


def row_pair(m, found, pairs):
    """혼자 쓴 글이 줄이 될 때의 짝 {"term", "v"} 또는 None. 숫자는 첫머리의 첫 숫자 하나만 본다 — 시세 수준이거나 한 곳만 쓴 숫자로
    싣기 어려운 꼴(R.solo_num_ok)이면 숫자를 싣지 않는다(다음 숫자로 넘어가지 않는다). 숫자와 짝짓는 낱말은 그 숫자 바로 곁
    (row_term_chars자 안)의 A·B급 낱말이어야 한다 — 두 곳이 확인하지 않은 숫자라 숫자 칸보다 좁게 본다.
    짝이 없으면 숫자 없는 줄(v None): 첫 두 줄의 대표 낱말(head_top). 그것도 없으면 줄이 없다."""
    v = m["lead_nums"][0] if m["lead_nums"] else None
    term = R.named_before(found["hits"], pairs[v][2], TH["row_term_chars"]) if v in pairs else None
    if term in m["lead"] and R.solo_num_ok(v):
        return {"term": term, "v": v}
    top = head_top(m)
    return {"term": top, "v": None} if top else None


def head_top(m):
    """숫자 없는 줄의 낱말 — 첫 두 줄에서 가장 먼저 나온 A·B급 낱말. A·B급이 없으면 그 글의 낱말이 둘 이상일 때만 첫 두 줄의
    첫 낱말(흔한 C급 낱말 하나만 있는 글은 줄이 되지 않는다). 첫 두 줄에 낱말이 없으면 None."""
    head = m["head"]
    return next((t for t in head if R.grade_of(t) in AB), head[0] if head and len(m["terms"]) > 1 else None)


def lead_top(m):
    """글의 대표 낱말 — 첫머리에서 가장 먼저 나온 A·B급 낱말, 그런 낱말이 없으면 가장 먼저 나온 낱말. 낱말이 없으면 None.
    ('금리' 같은 흔한 C급 낱말이 제목의 주제를 가리지 않게 A·B급을 앞세우고, A·B급끼리는 제목에 먼저 나온 쪽을 따른다.)"""
    return next((t for t in m["lead"] if R.grade_of(t) in AB), m["lead"][0] if m["lead"] else None)


def _is_level(v, before):
    """금리 수준·변동 폭으로 보이는 숫자인가 — 바로 앞 낱말이 기술적(금리 수준·커브) 낱말이고 단위가 %·bp일 때."""
    return bool(before) and R.num_unit(v)[1] in ("%", "bp") and R.TERMS[before[-1]["term"]]["factor"] == "기술적"


def num_pairs(text, found=None):
    """글의 숫자(시세 수준 제외) → {숫자: (낱말, 결과 낱말, 자리)}. 낱말은 숫자 앞 num_term_chars자 안의 가장 가까운 A·B급 낱말
    (R.named_before — 없으면 None), 결과 낱말은 숫자 곁 num_result_chars자 안에서 가장 가까운 것(없으면 None)."""
    found = found or scan(text)
    terms, results, reach, out = found["terms"], found["results"], TH["num_result_chars"], {}
    for n in found["nums"]:
        v, at = n["v"], n["pos"]
        before = [t for t in terms if t["pos"] < at]
        if R.is_quote(v) or _is_level(v, before):
            continue
        near = [r for r in results if -reach - len(r["result"]) <= r["pos"] - at <= reach + len(v)]
        out[v] = (R.named_before(found["hits"], at), min(near, key=lambda r: abs(r["pos"] - at))["result"] if near else None, at)
    return out


def shingles(text):
    """글 지문 — 주소를 빼고 글자·숫자만 남긴 글의 5-gram 집합. 조각이 min_chars개가 안 되는 짧은 글은 지문이 없다."""
    flat = "".join(c for c in _URL_IN_TEXT.sub(" ", R.norm_text(text)).casefold() if c.isalnum())
    grams = {flat[i:i + TH["ngram"]] for i in range(len(flat) - TH["ngram"] + 1)}
    return frozenset(grams) if len(grams) >= TH["min_chars"] else frozenset()


def _event_keys(m, at, events):
    """일정 열쇠 — 첫머리에 그 일정의 낱말이 있고 일정 뒤 num_key_hours 안(시각이 없는 일정은 그날)에 올린 글."""
    out = set()
    for e in events:
        start = S.parse_iso(f"{e['date']}T{e['time'] or '00:00'}:00+09:00")
        span = datetime.timedelta(hours=TH["num_key_hours"]) if e["time"] else datetime.timedelta(days=1)
        if e["term"] in m["lead"] and start <= at < start + span:
            out.add(S.key_of("k", f"e|{e['term']}|{e['date']}"))
    return out


def _phase(m):
    """1 원천 채널이 직접 쓴 글 · 2 원천 채널의 전달 글 · 3 주제 한정 · 4 속보형 · 0 참고(늘 혼자)."""
    if m["role"] == "source":
        return 2 if m["fwd"] else 1
    return {"topic": 3, "wire": 4}.get(m["role"], 0)


def _item(post, group, role, footers, events):
    """묶는 동안 쓰는 글 하나 — 닫힌 값(m)과 열쇠·지문·숫자 짝. 원문은 담지 않는다."""
    found = scan(post["text"])
    pairs = num_pairs(post["text"], found)
    m, at = mention(post, group, role, found, pairs), S.parse_iso(post["at"])
    top, phase = lead_top(m), _phase(m)
    keyed = phase == 1 and group in KEY_GROUPS
    topic = {S.key_of("k", f"{top}|{R.TERMS[top]['region']}")} if keyed and top and R.grade_of(top) in AB else set()
    return {"m": m, "at": at, "phase": phase, "keys": post_keys(post, footers), "origin": fwd_origin(post), "topic": topic,
            "event": _event_keys(m, at, events) if keyed else set(), "sh": shingles(post["text"]), "pairs": pairs}


# ---------- 묶기 ----------

class _Groups:
    """합집합 찾기. 묶음의 대표는 늘 가장 이른 글이고, 합친 묶음이 cluster_max_posts글을 넘게 되면 합치지 않는다."""

    def __init__(self, n):
        self.up, self.size = list(range(n)), [1] * n

    def find(self, i):
        while self.up[i] != i:
            self.up[i] = self.up[self.up[i]]
            i = self.up[i]
        return i

    def join(self, a, b):
        """합쳤거나 이미 같은 묶음이면 True, 상한에 걸려 못 합쳤으면 False."""
        a, b = sorted((self.find(a), self.find(b)))
        if a != b and self.size[a] + self.size[b] > TH["cluster_max_posts"]:
            return False
        if a != b:
            self.up[b], self.size[a] = a, self.size[a] + self.size[b]
        return True


def similar_pairs(items):
    """글 지문이 닮은 쌍 {(i, j)} (i < j) — 자카드 jaccard_min 이상 또는 포함도 contain_min 이상. 같은 채널의 글끼리는 보지 않는다."""
    index, out = collections.defaultdict(dict), set()       # 조각 → {채널: 그 조각이 있는 글들}
    for j, it in enumerate(items):
        ch, share = it["m"]["ch"], collections.Counter()
        for g in it["sh"]:
            for other, seen in index[g].items():
                if other != ch:                             # 같은 채널의 꼬리말 문장을 세느라 느려지지 않게 건너뛴다
                    share.update(seen)
            index[g].setdefault(ch, []).append(j)
        for i, n in share.items():
            a, b = len(items[i]["sh"]), len(it["sh"])
            if n / (a + b - n) >= TH["jaccard_min"] or n / min(a, b) >= TH["contain_min"]:
                out.add((i, j))
    return out


def _num_key(a, b):
    """두 글이 num_key_hours 안에 같은 A·B급 낱말과 짝지은 같은 숫자 num_key_nums개(시세 제외)를 썼으면 n 열쇠, 아니면 None.
    숫자만 같고 짝지은 낱말이 다르거나 없으면 세지 않는다. 같은 채널의 두 글은 맞추지 않는다."""
    if a["m"]["ch"] == b["m"]["ch"] or min(len(a["pairs"]), len(b["pairs"])) < TH["num_key_nums"]:
        return None                                # 흔한 경우를 먼저 걸러 낸다(글 수의 제곱만큼 불린다)
    nums = sorted(v for v in set(a["pairs"]) & set(b["pairs"]) if a["pairs"][v][0] and a["pairs"][v][0] == b["pairs"][v][0])
    near = abs(a["at"] - b["at"]) <= datetime.timedelta(hours=TH["num_key_hours"])
    if not near or len(nums) < TH["num_key_nums"]:
        return None
    return S.key_of("n", "|".join(nums[:TH["num_key_nums"]] + [a["pairs"][nums[0]][0]]))


def _by_keys(items, base, groups):
    """같은 열쇠를 가진 글끼리 — 열쇠마다 가장 이른 글에 붙인다(가득 차면 다음 글부터 새 묶음). 주제 열쇠는 이어지는 글 사이가
    topic_key_hours 안일 때만 잇는다."""
    strong, topic = collections.defaultdict(list), collections.defaultdict(list)
    for i in base:
        for k in items[i]["keys"] | items[i]["event"]:
            strong[k].append(i)
        for k in items[i]["topic"]:
            topic[k].append(i)
    for k in sorted(strong, key=_key_order):
        head = strong[k][0]
        for i in strong[k][1:]:
            head = head if groups.join(head, i) else i
    gap = datetime.timedelta(hours=TH["topic_key_hours"])
    for k in sorted(topic):
        for a, b in zip(topic[k], topic[k][1:]):
            if items[b]["at"] - items[a]["at"] <= gap:
                groups.join(a, b)


def _by_numbers(items, base, groups):
    """숫자 열쇠 — 묶음의 씨앗 글(가장 이른 글)끼리 맞을 때만 합친다. 뒤의 글을 거쳐 사슬처럼 이어 붙지 않는다."""
    seeds = []
    for s in sorted({groups.find(i) for i in base}):
        if len(items[s]["pairs"]) < TH["num_key_nums"]:
            continue
        if not any(_num_key(items[r], items[s]) and groups.join(r, s) for r in seeds):
            seeds.append(s)


def _home(p, items, base, groups, sim):
    """글 p가 가장 많이 맞는 묶음 하나(그 묶음의 가장 이른 바탕 글) 또는 None. 같이 가진 열쇠 하나하나 · 닮은 지문 · 씨앗 글과의
    숫자가 한 번씩 센다. 맞은 수가 같으면 더 이른 묶음."""
    hits, seed = collections.defaultdict(set), {}
    for i in base:
        root = groups.find(i)
        seed.setdefault(root, i)
        hits[root] |= items[i]["keys"] & items[p]["keys"]
        if (min(i, p), max(i, p)) in sim:
            hits[root].add("g")
    for root, s in seed.items():
        if _num_key(items[s], items[p]):
            hits[root].add("n")
    best = max((r for r in hits if hits[r]), key=lambda r: (len(hits[r]), -seed[r]), default=None)
    return None if best is None else seed[best]


def _forwards(items, base, groups, sim):
    """원천 채널의 전달 글 — 맞는 묶음이 있으면 거기에 붙이고, 없으면 전달 원글이 같은 것끼리만 묶는다. → 새 바탕이 된 글들"""
    alone, first = [], {}
    for p in (i for i, it in enumerate(items) if it["phase"] == 2):
        home = _home(p, items, base, groups, sim)
        if home is None or not groups.join(home, p):
            alone.append(p)
    for p in alone:
        origin = items[p]["origin"]
        if origin and not groups.join(first.setdefault(origin, p), p):
            first[origin] = p                      # 가득 찬 묶음 — 이 글부터 새로 묶는다
    return alone


def link_posts(items):
    """시각순으로 놓인 글들 → (합집합 찾기, 닮은 쌍). 원천 글끼리 먼저 묶고 나머지를 한 곳에만 붙인다."""
    groups, sim = _Groups(len(items)), similar_pairs(items)
    base = [i for i, it in enumerate(items) if it["phase"] == 1]
    _by_keys(items, base, groups)
    for i, j in sorted(sim):
        if items[i]["phase"] == items[j]["phase"] == 1:
            groups.join(i, j)
    _by_numbers(items, base, groups)
    base = sorted(base + _forwards(items, base, groups, sim))
    for phase in (3, 4):
        for p in (i for i, it in enumerate(items) if it["phase"] == phase):
            home = _home(p, items, base, groups, sim)
            if home is not None:
                groups.join(home, p)
    return groups, sim


# ---------- 묶음 하나의 꼴 ----------

def _key_order(k):
    return (S.KEY_KINDS.index(k[0]), k)


def _tally(members, field):
    """낱말·결과 낱말 → 그것을 쓴 채널 수(한 채널은 한 번만 센다)."""
    seen = collections.defaultdict(set)
    for m in members:
        for x in m[field]:
            seen[x].add(m["ch"])
    return {k: len(v) for k, v in seen.items()}


def _term_order(kv):
    """묶음의 낱말 순서 — 두 곳 이상이 쓴 낱말이 먼저, 그 안에서 A·B급 → 쓴 채널이 많은 순(같으면 등급 · 가나다).
    한 곳만 쓴 A·B급 낱말이 여러 곳이 쓴 낱말을 제목에서 밀어내지 않게 한다."""
    term, n = kv
    return (n < SHARED_MIN, R.grade_of(term) not in AB, -n, R.GRADES.index(R.grade_of(term)), term)


def _majority(votes):
    """과반이 고른 값. 없으면 None."""
    top = collections.Counter(votes).most_common(1)
    return top[0][0] if top and top[0][1] * 2 > len(votes) else None


def cell_of(members):
    """분류 칸 — 채널마다 대표 낱말의 칸 하나(원천 채널이 낱말을 썼으면 원천 채널만), 과반이 같을 때만 그 칸.
    갈리면 기타(분류 보류 — 지역은 과반이 같으면 그 지역, 아니면 글로벌), 첫머리 낱말이 하나도 없으면 None."""
    voters = [m for m in members if m["lead"]]
    pool, votes = [m for m in voters if m["role"] == "source"] or voters, {}
    for m in sorted(pool, key=lambda m: (m["fwd"], m["at"], m["id"])):
        entry = R.TERMS[lead_top(m)]
        votes.setdefault(m["ch"], (entry["factor"], entry["region"]))
    if not votes:
        return None
    cell = _majority(list(votes.values())) or ("기타", _majority([r for _, r in votes.values()]) or R.REGIONS[0])
    return {"factor": cell[0], "region": cell[1]}


def shape(members, keys, nums=()):
    """닫힌 값의 글들 → 묶음 하나(계약의 cluster 꼴). keys = 묶을 때 쓴 열쇠들, nums = 숫자 칸. 낱말은 첫머리 것만 세고
    결과 낱말은 직접 쓴 글(전달 제외)의 것만 센다."""
    ms = sorted((dict(m) for m in members), key=lambda m: (m["at"], m["ch"], m["id"]))
    terms = sorted(_tally(ms, "lead").items(), key=_term_order)[:MAX_WORDS]
    results = sorted(_tally([m for m in ms if not m["fwd"]] or ms, "results").items(), key=lambda kv: (-kv[1], kv[0]))
    keys = sorted(set(keys), key=_key_order)[:MAX_KEYS]
    return {"seed": S.seed_of(ms), "key": S.primary_key(keys), "keys": keys, "first_at": ms[0]["at"], "last_at": ms[-1]["at"],
            "cell": cell_of(ms), "terms": [{"term": t, "n_ch": n} for t, n in terms],
            "results": [{"result": r, "n_ch": n} for r, n in results], "nums": [dict(n) for n in nums], "members": ms}


def _shared_nums(its):
    """숫자 칸 — 원천 채널 SHARED_MIN곳 이상이 직접 쓴 글에서 같은 낱말과 짝지은 같은 숫자, 많이 쓴 순으로 nums_max개까지.
    낱말 짝이 없는 숫자는 싣지 않는다(묶음의 대표 낱말에 대신 붙이지 않는다). 결과 낱말은 그 채널들의 과반(SHARED_MIN곳 이상)이
    같이 쓴 것만."""
    first = {}                                     # (채널, 숫자) → (낱말, 결과 낱말, 처음 쓴 자리)
    for it in its:
        m = it["m"]
        if m["role"] == "source" and not m["fwd"]:
            for v, (term, result, pos) in it["pairs"].items():
                if term:
                    first.setdefault((m["ch"], v), (term, result, (m["at"], m["ch"], m["id"], pos)))
    by = collections.defaultdict(list)
    for (_, v), (term, result, order) in first.items():
        by[(term, v)].append((order, result))
    rows = []
    for (term, v), got in by.items():
        said = collections.Counter(r for _, r in got if r).most_common()
        best = min(said, key=lambda x: (-x[1], x[0]), default=(None, 0))
        agreed = best[1] >= SHARED_MIN and best[1] * 2 > len(got)
        if len(got) >= SHARED_MIN:
            rows.append((-len(got), min(o for o, _ in got), {"term": term, "result": best[0] if agreed else None, "v": v,
                                                             "n_ch": len(got)}))
    return [row for _, _, row in sorted(rows, key=lambda r: r[:2])[:TH["nums_max"]]]


def _cluster(idx, items, sim):
    """글 번호들(시각순) → 묶음 하나. 열쇠는 두 글 이상이 함께 가진 것 + 씨앗 글과 맞은 숫자 열쇠 + (지문·혼자면) g."""
    its = [items[i] for i in idx]
    seed = S.seed_of([it["m"] for it in its])
    origin = next(it for it in its if (it["m"]["ch"], it["m"]["id"]) == (seed["ch"], seed["id"]))
    count = collections.Counter(k for it in its for k in it["keys"] | it["topic"] | it["event"])
    keys = {k for k, n in count.items() if n > 1} | ({_num_key(origin, it) for it in its} - {None})
    if not keys or any((a, b) in sim for a in idx for b in idx if a < b):
        keys.add(S.key_of("g", f"{seed['ch']}/{seed['id']}"))
    draft = shape([it["m"] for it in its], keys)
    return {**draft, "nums": _shared_nums(its) if draft["terms"] else []}


def cluster_posts(doc, status, events=()):
    """posts.json의 자료 + collect_status.json의 자료 → clusters.json의 자료. 입력은 고치지 않는다.
    events(events_of의 꼴)를 주면 일정 열쇠도 쓴다. 수집 상태에 없는 채널의 글이 있으면 ValueError."""
    roles = {c["ch"]: (c["group"], c["role"]) for c in status["channels"]}
    posts = sorted(doc["posts"], key=lambda p: (p["at"], p["ch"], p["id"]))
    if any(p["ch"] not in roles for p in posts):
        raise ValueError("수집 상태에 없는 채널의 글이 있음")
    footers, dropped, kept = footer_links(posts), dict.fromkeys(R.DROP_CODES, 0), []
    for p in posts:
        code = R.drop_code(p["text"], len(_links(p) - footers[p["ch"]]))
        if code:
            dropped[code] += 1
        else:
            kept.append(p)
    items = [_item(p, *roles[p["ch"]], footers[p["ch"]], events) for p in kept]
    groups, sim = link_posts(items)
    by = collections.defaultdict(list)
    for i in range(len(items)):
        by[groups.find(i)].append(i)
    clusters = sorted((_cluster(idx, items, sim) for idx in by.values()), key=lambda c: (c["first_at"], c["seed"]["ch"], c["seed"]["id"]))
    return {"schema": S.SCHEMA, "edition": doc["edition"], "window": dict(doc["window"]), "collected_at": doc["collected_at"],
            "stats": {"posts": len(posts), "kept": len(kept), "dropped": dropped}, "clusters": clusters}


# ---------- 일정 (묶기의 일정 열쇠와 점수의 E · '내일 볼 것'이 같이 쓴다) ----------

def _amount(offered_100m):
    """발행 예정액(억 원) → "2.4조원" 꼴. 읽을 수 없으면 None."""
    if type(offered_100m) not in (int, float) or not 0 < offered_100m < 10_000_000:
        return None
    v = f"{offered_100m / 10_000:.2f}".rstrip("0").rstrip(".") + "조원"
    return v if R.is_num(v) else None


def _is_day(s):
    try:
        return bool(isinstance(s, str) and S.DATE_RE.fullmatch(s) and datetime.date.fromisoformat(s))
    except ValueError:
        return False


def _auction_rows(korea, field):
    """korea.json의 입찰 줄들 가운데 날짜와 만기를 읽을 수 있는 것만. 꼴이 다르면 빈 목록(닫힌 쪽으로)."""
    box = korea.get("calendar") if field == "rows" and isinstance(korea, dict) else korea
    rows = box.get(field) if isinstance(box, dict) else None
    return [r for r in rows if isinstance(r, dict) and _is_day(r.get("date")) and r.get("tenor") in R.TENORS] \
        if isinstance(rows, list) else []


def events_of(calendar, korea):
    """일정 → [{"date", "time", "term", "tier", "detail", "src"}] 날짜·시각·낱말순. 달력(calendar.json)의 일정과 korea.json의 국고채
    입찰 일정(10·30년 A, 그 밖 B. 발행 예정액을 알면 detail에 만기와 함께). 둘 다 없으면 빈 목록."""
    out = [{"date": e["date"], "time": e.get("time"), "term": e["term"], "tier": e["tier"], "detail": list(e.get("detail") or []),
            "src": "calendar"} for e in (calendar or {}).get("events", [])]
    offered = {(r["date"], r["tenor"]): _amount(r.get("offered_100m")) for r in _auction_rows(korea, "offerings")}
    for r in _auction_rows(korea, "rows"):
        amount = offered.get((r["date"], r["tenor"]))
        out.append({"date": r["date"], "time": None, "term": AUCTION_TERM, "tier": "A" if r["tenor"] in AUCTION_A else "B",
                    "detail": [r["tenor"]] + ([amount] if amount else []), "src": "korea"})
    return sorted(out, key=lambda e: (e["date"], e["time"] or "", e["term"]))


# ---------- 실행 ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description="저녁판 묶기 — posts.json의 글을 같은 일끼리 묶어 clusters.json을 쓴다(원문을 읽는 마지막 단계)")
    ap.add_argument("--work", default=S.WORK, help="작업 폴더 (기본: .work/evening)")
    ap.add_argument("--calendar", help="일정 열쇠를 켤 때만: calendar.json")
    ap.add_argument("--korea", help="일정 열쇠를 켤 때만: korea.json(국고채 입찰 일정)")
    a = ap.parse_args(argv)
    doc = S.validate_posts_doc(S.read_json(os.path.join(a.work, "posts.json")))
    status = S.validate_collect_status(S.read_json(os.path.join(a.work, "collect_status.json")))
    if (doc["edition"], doc["window"]) != (status["edition"], status["window"]):
        raise ValueError("posts.json과 collect_status.json의 판이 다름")
    calendar = S.validate_calendar(S.read_json(a.calendar)) if a.calendar else None
    events = events_of(calendar, S.read_json(a.korea, None) if a.korea else None)
    out = S.validate_clusters_doc(cluster_posts(doc, status, events))
    S.write_json(os.path.join(a.work, "clusters.json"), out)
    st = out["stats"]
    S.report("digest_cluster", posts=st["posts"], kept=st["kept"], dropped=sum(st["dropped"].values()), clusters=len(out["clusters"]),
             joined=sum(len(c["members"]) > 1 for c in out["clusters"]))
    return 0


if __name__ == "__main__":
    sys.exit(S.run_cli("digest_cluster", main))
