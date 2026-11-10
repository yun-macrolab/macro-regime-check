#!/usr/bin/env python3
"""연준 인물 새 발언 게시(people_push) 테스트 — 약속대로 다시 검사하는가, 그 파일 하나만 올리는가, 멈추면 폴더를 깨끗이 두는가.

실행:  python -X utf8 scripts/test_people_push.py   (아침 묶음 `python -m unittest discover -s scripts`가 함께 돈다)
네트워크 불필요 — git · 공개 전 검사는 가짜 실행기(부른 명령을 적고 정해 둔 답을 준다)이고, 끝의 묶음만 임시 폴더의 진짜 git으로 돈다
(원격도 그 안의 bare 저장소). 발언 · 사람 · 출처는 지어낸 것이고, 명단은 임시 폴더에 쓴 작은 people-data.js다.
끝의 DataFileTest는 저장소에 data/people_remarks.json이 있으면 그 파일을 게시기와 같은 검사로 본다(CI가 배포 전에).
칸 전체를 내려 scripts/people_push.py를 지운 저장소에서는 묶음 전체를 건너뛴다(공개 파일까지 지웠을 때만 — TakedownTest).
"""
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
# 칸 전체를 내린 저장소(README '보류 · 내리기' — scripts/people_push.py와 data/people_remarks.json을 함께 지운다)에서는 이 묶음을 건너뛴다.
# 지우지 않으면 아침 검사가 import에서 떨어져 내리는 push가 배포되지 않고 그 뒤 예약 갱신도 멈춘다(audit 2026-11-10 c-pub-repo-01).
# 게시기만 지우고 공개 파일이 남았으면 그 파일을 검사할 길이 없으니 건너뛰지 않고 떨어진다(DataFileTest의 배포 앞 검사를 조용히 잃지 않게).
if not os.path.exists(os.path.join(HERE, "people_push.py")):
    if os.path.exists(os.path.join(REPO, "data", "people_remarks.json")):
        raise ImportError("scripts/people_push.py가 없는데 data/people_remarks.json이 남아 있다 — 칸 전체를 내릴 때는 두 파일을 함께 "
                          "지운다(README '보류 · 내리기')")
    raise unittest.SkipTest("scripts/people_push.py를 지웠다(발언 칸 전체를 내림 — README '보류 · 내리기')")
import people_push as P

TODAY = datetime.date(2026, 11, 4)
PATH = "data/people_remarks.json"
MOD, NEW = f" M {PATH}\n", f"?? {PATH}\n"
PICKS = "data/digest_picks.json"
PUSH = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential", "push", "origin", "HEAD:main"]
MSG = "data: 2026-11-04 연준 인물 발언"
CANARY = "카나리아-글자-zz9"                      # 파일의 글 — 로그 · 오류 문구 어디에도 나오면 안 된다
KEYS = ("warsh", "cook", "hammack")
ROSTER_JS = "/* 명단 */\nwindow.PEOPLE_DATA = %s;\n"


def remark(who="warsh", said_on="2026-10-28", venue="기자회견", **over):
    r = {"id": P.remark_id(who, said_on, venue), "who": who, "said_on": said_on, "venue": venue, "access": "직접",
         "topic": "AI 투자·금융여건", "quote": "rates find the cracks", "vs_base": "평소보다 비둘기",
         "basis": [{"path": "baseline.dove_surprise[2]", "text": "고용 약화를 주된 위험으로·2027 인하"}],
         "why": "고용 위험을 앞세움", "conditional": "", "dissent": "", "source": "Reuters", "title": "지어낸 제목 " + CANARY,
         "tags": ["기준선 초안"], "baseline_asof": "2026-10-31", "baseline_review": "draft"}
    r.update(over)
    return r


def source(remarks=None, **over):
    d = {"schema": P.SCHEMA, "generated_at": "2026-11-04T13:05:12+09:00", "window_from": "2025-11-04",
         "remarks": [remark(), remark("cook", "2026-10-28", "투표", vs_base="평소보다 매파", dissent="인상", quote=""),
                     remark("hammack", "2026-10-24", "연설", vs_base="평소와 같음")] if remarks is None else remarks,
         "held": 2}
    d.update(over)
    return d


def enc(doc, pretty=True):
    return json.dumps(doc, ensure_ascii=False, indent=1 if pretty else None).encode("utf-8")


def why_of(doc_or_raw, keys=KEYS, today=TODAY):
    raw = doc_or_raw if isinstance(doc_or_raw, bytes) else enc(doc_or_raw)
    try:
        P.check_source(raw, set(keys), today)
    except P.Bad as e:
        return e.why
    return None


# ---------- 가짜 git ----------

def name_of(cmd):
    if cmd[0] != "git":
        return "blind" if cmd[-1].replace("\\", "/").endswith("scripts/check_blind.py") else "other"
    rest = list(cmd[1:])
    while rest and rest[0] == "-c":
        rest = rest[2:]
    return rest[0]


class Tool:
    """가짜 git · 공개 전 검사 — answers = {이름: 답 | [차례로 줄 답들] | 함수}. 답은 종료코드나 (종료코드, 출력), 예외면 던진다."""

    def __init__(self, **answers):
        self.calls, self.kw = [], []
        self.answers = {k.replace("_", "-"): v for k, v in answers.items()}

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        self.kw.append(kw)
        got = self.answers.get(name_of(cmd), 0)
        if callable(got):
            got = got(cmd)
        elif isinstance(got, list):
            got = got.pop(0) if len(got) > 1 else got[0]
        if isinstance(got, BaseException):
            raise got
        code, out = got if isinstance(got, tuple) else (got, "")
        return types.SimpleNamespace(returncode=code, stdout=out.encode("utf-8"), stderr=b"")

    def names(self):
        return [name_of(c) for c in self.calls]

    def count(self, name):
        return self.names().count(name)


def good(**more):
    """모두 잘 되는 날 — 바뀐 것은 발언 파일 하나(처음 생김), main의 끝, 커밋 1개."""
    return {"status": (0, NEW), "rev_parse": lambda cmd: (0, "aaa111\naaa111\n" if "HEAD" in cmd else "aaa111\n"),
            "rev_list": (0, "1\n"), "diff": (0, PATH + "\n"), **more}


class Case(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.put_roster(KEYS)
        self.file = os.path.join(self.repo, "data", "people_remarks.json")
        self.src = os.path.join(self.repo, "..", os.path.basename(self.repo) + "-people-remarks.json")
        self.addCleanup(lambda: os.path.exists(self.src) and os.remove(self.src))

    def put_roster(self, keys):
        os.makedirs(os.path.join(self.repo, "site"), exist_ok=True)
        with open(os.path.join(self.repo, "site", "people-data.js"), "w", encoding="utf-8") as f:
            f.write(ROSTER_JS % json.dumps({"asof": "2026-10-31", "people": [{"key": k, "name_ko": k} for k in keys]}))

    def put_source(self, doc):
        with open(self.src, "wb") as f:
            f.write(doc if isinstance(doc, bytes) else enc(doc))

    def public(self, doc=None):
        return P.check_source(enc(doc or source()), set(KEYS), TODAY)

    def put_published(self, doc):
        os.makedirs(os.path.dirname(self.file), exist_ok=True)
        with open(self.file, "wb") as f:
            f.write(P.dump(doc))

    def raw(self):
        with open(self.file, "rb") as f:
            return f.read()

    def clear(self):
        """publish는 멈춰도 쓴 파일을 두고 간다(정리는 run_all의 몫) — 다음 경우를 위해 지운다."""
        if os.path.exists(self.file):
            os.remove(self.file)

    def stops(self, code, fn, *a, **kw):
        with self.assertRaises(P.Stop) as cm:
            fn(*a, **kw)
        self.assertEqual(cm.exception.code, code)
        self.assertEqual(str(cm.exception), code)                  # 메시지는 코드뿐이다
        return cm.exception


# ---------- 약속 ----------

class ContractTest(unittest.TestCase):
    def test_constants_are_the_contract(self):
        self.assertEqual(P.SCHEMA, "people-remarks/1")
        self.assertEqual(P.VENUES, ("기자회견", "연설", "인터뷰", "의회 증언", "투표", "의사록", "기고", "기타"))
        self.assertEqual(P.ACCESS, ("직접", "전언"))
        self.assertEqual(P.VS_BASE, ("평소와 같음", "평소보다 매파", "평소보다 비둘기", "새 주제"))
        self.assertEqual(P.SIDES, ("인상", "인하", "동결", "문구"))
        self.assertEqual(P.TAGS, ("블랙아웃 중 — 전언 확인", "기준선 초안"))
        self.assertEqual(P.REVIEWS, ("draft", "approved"))
        self.assertEqual((P.PER_PERSON, P.MAX_ITEMS, P.MAX_BYTES, P.QUOTE_WORDS), (30, 400, 256 * 1024, 15))
        self.assertEqual(P.LIMITS, {"topic": 40, "why": 120, "conditional": 80, "source": 40, "title": 80})
        self.assertEqual((P.BASIS_MAX, P.BASIS_TEXT), (4, 120))
        self.assertEqual(len(P.FIELDS), 17)
        self.assertEqual(P.SOURCE_KEYS, ("schema", "generated_at", "window_from", "remarks", "held"))
        self.assertEqual(P.PUBLIC_KEYS, ("schema", "asof", "window_from", "remarks", "held"))

    def test_id_rule(self):
        want = hashlib.sha1("warsh|2026-10-28|기자회견".encode("utf-8")).hexdigest()[:12]
        self.assertEqual(P.remark_id("warsh", "2026-10-28", "기자회견"), want)
        self.assertRegex(want, r"^[0-9a-f]{12}$")
        self.assertNotEqual(P.remark_id("warsh", "2026-10-28", "연설"), want)

    def test_same_git_patterns_as_the_evening_publisher(self):
        PP = P._picks()                                                       # 게시기가 sync에 쓰는 저녁판 게시기 그대로
        self.assertEqual((P.PUSH, P.STATUS, P.GIT_S, P.CHECK_S), (PP.PUSH, PP.STATUS, PP.GIT_S, PP.CHECK_S))
        self.assertNotEqual(P.PATH, PP.PATH)
        self.assertEqual([x.replace(P.PATH, "") for x in P.CHANGED + P.STAGED], [x.replace(PP.PATH, "") for x in PP.CHANGED + PP.STAGED])

    def test_module_loads_without_the_evening_code(self):
        """비공개 쪽 짝 테스트는 상수만 본다 — 이 모듈을 싣는 것만으로 저녁판 코드가 실리지 않는다."""
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import people_push; "
                            "print('picks_push' in sys.modules, 'digest_schema' in sys.modules)", HERE], capture_output=True, timeout=60)
        self.assertEqual(r.stdout.decode().split(), ["False", "False"])


class ConvertTest(unittest.TestCase):
    def test_good_source_becomes_the_public_form(self):
        doc = source()
        doc["remarks"] = list(reversed(doc["remarks"]))                       # 차례는 게시기가 맞춘다
        pub = P.check_source(enc(doc), set(KEYS), TODAY)
        self.assertEqual(list(pub), list(P.PUBLIC_KEYS))
        self.assertEqual(pub["asof"], "2026-11-04")
        self.assertNotIn("generated_at", pub)
        self.assertEqual([(r["said_on"], r["who"], r["venue"]) for r in pub["remarks"]],
                         [("2026-10-28", "cook", "투표"), ("2026-10-28", "warsh", "기자회견"), ("2026-10-24", "hammack", "연설")])
        self.assertTrue(all(list(r) == list(P.FIELDS) for r in pub["remarks"]))
        raw = P.dump(pub)
        self.assertNotIn(b"\n", raw)                                          # 한 줄 JSON(저녁판 파일과 같은 꼴)
        self.assertEqual(P.check_public(raw, set(KEYS), TODAY), pub)

    def test_order_within_a_day_is_person_then_venue(self):
        rs = [remark("warsh", "2026-10-28", "투표", vs_base="평소와 같음", quote=""), remark("warsh", "2026-10-28", "기자회견"),
              remark("cook", "2026-10-29", "연설")]
        got = P.check_source(enc(source(rs)), set(KEYS), TODAY)["remarks"]
        self.assertEqual([(r["said_on"], r["venue"]) for r in got], [("2026-10-29", "연설"), ("2026-10-28", "기자회견"), ("2026-10-28", "투표")])

    def test_empty_list_is_a_valid_file(self):
        pub = P.check_source(enc(source([], held=0)), set(KEYS), TODAY)
        self.assertEqual((pub["remarks"], pub["held"]), ([], 0))

    def test_quote_can_be_cut_at_fifteen_words(self):
        words = " ".join(f"w{i}" for i in range(15))
        self.assertIsNone(why_of(source([remark(quote=words)])))
        self.assertIsNone(why_of(source([remark(quote=words + " " + P.CUT)])))
        self.assertEqual(why_of(source([remark(quote=words + " w15")])), "quote")
        self.assertEqual(why_of(source([remark(quote=words + " w15 " + P.CUT)])), "quote")
        self.assertEqual(why_of(source([remark(quote=" ".join(f"w{i}" for i in range(14)) + " " + P.CUT + " w")])), "quote")

    def test_limits_are_inclusive(self):
        for k, n in P.LIMITS.items():
            with self.subTest(k):
                self.assertIsNone(why_of(source([remark(**{k: "가" * n})])))
                self.assertEqual(why_of(source([remark(**{k: "가" * (n + 1)})])), k)
        self.assertIsNone(why_of(source([remark(basis=[{"path": "a" * 80, "text": "가" * 120}] * 4)])))

    def test_dates_up_to_one_day_ahead(self):
        self.assertIsNone(why_of(source(generated_at="2026-11-05T00:30:00+09:00", window_from="2025-11-05")))
        self.assertEqual(why_of(source(generated_at="2026-11-06T00:30:00+09:00", window_from="2025-11-06")), "asof")
        self.assertIsNone(why_of(source([remark(baseline_asof="2026-11-05")])))
        self.assertEqual(why_of(source([remark(baseline_asof="2026-11-06")])), "baseline_asof")
        self.assertIsNone(why_of(source(window_from="2025-11-03")))           # 366일 — 비공개 쪽이 자정을 넘긴 날
        self.assertEqual(why_of(source(window_from="2025-11-02")), "window_from")

    def test_thirty_per_person_and_four_hundred_in_all(self):
        day = lambda i: (datetime.date(2026, 11, 3) - datetime.timedelta(days=i)).isoformat()
        thirty = [remark(said_on=day(i)) for i in range(30)]
        self.assertIsNone(why_of(source(thirty)))
        self.assertEqual(why_of(source(thirty + [remark(said_on=day(30))])), "per_person")
        many = [remark(k, day(i), v) for k in KEYS for i in range(34) for v in P.VENUES[:4]][:401]
        self.assertEqual(why_of(source(many)), "count")                        # 개수 상한을 사람마다 셈보다 먼저 본다


class RuleTest(unittest.TestCase):
    """약속의 규칙마다 하나씩 어겨 본다 — 걸린 규칙 이름(why)이 그 규칙이어야 한다(다른 검사에 우연히 걸린 것이 아니게)."""

    def test_each_file_rule(self):
        base = source()
        cases = {
            "schema": [dict(base, schema="people-remarks/2"), {k: v for k, v in base.items() if k != "held"}, dict(base, extra=1),
                       dict({k: v for k, v in base.items() if k != "generated_at"}, asof="2026-11-04"), []],
            "generated_at": [dict(base, generated_at="2026-11-04T13:05:12"), dict(base, generated_at="2026-11-04 13:05:12+09:00"),
                             dict(base, generated_at="2026-11-04T25:05:12+09:00"), dict(base, generated_at=20261104)],
            "window_from": [dict(base, window_from="2026-11-05"), dict(base, window_from="2024-11-04")],
            "held": [dict(base, held=-1), dict(base, held="2"), dict(base, held=True), dict(base, held=1.5), dict(base, held=None)],
            "count": [dict(base, remarks={"a": 1}), dict(base, remarks=None)],
        }
        for why, docs in cases.items():
            for i, doc in enumerate(docs):
                with self.subTest(why=why, i=i):
                    self.assertEqual(why_of(doc), why)

    def test_each_remark_rule(self):
        bad_id = remark()
        bad_id["id"] = bad_id["id"].upper()
        r = remark()
        extra, missing = dict(r, more=1), {k: v for k, v in r.items() if k != "tags"}
        cases = {
            "fields": [extra, missing, "문자열", None],
            "who": [remark("powell"), remark("Warsh"), dict(r, who="")],
            "said_on": [remark(said_on="2026-10-32"), remark(said_on="2026/10/28"), remark(said_on="2025-11-03"), remark(said_on="2026-11-05")],
            "venue": [dict(r, venue="방송")], "access": [dict(r, access="간접")],
            "vs_base": [dict(r, vs_base="매파"), dict(r, vs_base=None)], "baseline_review": [dict(r, baseline_review="ok")],
            "id": [bad_id, dict(r, id=r["id"][:11]), dict(r, id=P.remark_id("warsh", "2026-10-28", "연설")), dict(r, id=12)],
            "quote": [dict(r, quote=" ".join(["w"] * 16))],
            "dissent": [dict(r, dissent="인상"), remark(venue="투표", dissent="반대"), remark(venue="투표", dissent=None)],
            "basis": [dict(r, basis=[]), dict(r, basis=[r["basis"][0]] * 5), dict(r, basis=[{"path": "baseline.usual[0]"}]),
                      dict(r, basis=[{"path": "baseline.usual[0]", "text": "x", "more": 1}]), dict(r, basis=[{"path": "baseline..usual", "text": "x"}]),
                      dict(r, basis=[{"path": "baseline.usual[x]", "text": "x"}]), dict(r, basis=[{"path": "a" * 81, "text": "x"}]),
                      dict(r, basis=[{"path": "baseline.usual[0]", "text": ""}]), dict(r, basis=[{"path": "baseline.usual[0]", "text": "가" * 121}]),
                      dict(r, basis="baseline.usual[0]")],
            "tags": [dict(r, tags=["기준선 확인"]), dict(r, tags=["기준선 초안", "기준선 초안"]), dict(r, tags="기준선 초안"), dict(r, tags=[1])],
            "baseline_asof": [dict(r, baseline_asof="2026-1-31"), dict(r, baseline_asof="")],
            "text": [dict(r, title="https://example.invalid/a"), dict(r, source="example.invalid://x"), dict(r, why="벨\x07소리"),
                     dict(r, why="폭없는​공백"), dict(r, topic="줄 구분"), dict(r, topic=" 앞 공백"), dict(r, title="뒤 공백 "),
                     dict(r, quote="tab\there"), dict(r, basis=[{"path": "baseline.usual[0]", "text": "주소 http://x"}]),
                     dict(r, conditional="﻿머리")],
            "topic": [dict(r, topic=5)],
        }
        for why, rs in cases.items():
            for i, x in enumerate(rs):
                with self.subTest(why=why, i=i):
                    self.assertEqual(why_of(source([x])), why)

    def test_one_remark_per_who_day_venue(self):
        self.assertEqual(why_of(source([remark(), remark(quote="other")])), "duplicate")

    def test_bytes_rules(self):
        self.assertEqual(why_of(b"not json " + CANARY.encode()), "json")
        self.assertEqual(why_of(b"\xff\xfe{}"), "json")
        self.assertEqual(why_of(b"[" * 100000 + b"]" * 100000), "json")       # 깊은 중첩도 예외 없이
        big = source([remark(said_on=(datetime.date(2026, 11, 3) - datetime.timedelta(days=i)).isoformat()) for i in range(30)])
        pad = enc(big)[:-1] + b" " * (P.MAX_BYTES) + b"}"
        self.assertEqual(why_of(pad), "size")
        self.assertRaises(P.Bad, P.check_source, "문자열", set(KEYS), TODAY)

    def test_error_text_carries_no_file_text(self):
        for doc in (source([remark(title="https://" + CANARY)]), source([remark(who=CANARY)]), b"{" + CANARY.encode()):
            try:
                P.check_source(doc if isinstance(doc, bytes) else enc(doc), set(KEYS), TODAY)
            except P.Bad as e:
                self.assertNotIn(CANARY, str(e) + repr(e.args) + str(e.why))
            else:
                self.fail("걸려야 한다")


class PublicFormTest(unittest.TestCase):
    def setUp(self):
        self.pub = P.check_source(enc(source()), set(KEYS), TODAY)

    def test_written_bytes_are_the_only_accepted_form(self):
        raw = P.dump(self.pub)
        self.assertEqual(P.check_public(raw, set(KEYS), TODAY), self.pub)
        bad = {
            "schema": [P.dump({k: self.pub[k] for k in ("asof", "schema", "window_from", "remarks", "held")}),   # 칸 차례
                       P.dump(dict(self.pub, generated_at="2026-11-04T13:05:12+09:00"))],
            "bytes": [json.dumps(self.pub, ensure_ascii=False, indent=1).encode("utf-8"), raw + b"\n",
                      P.dump(dict(self.pub, remarks=list(reversed(self.pub["remarks"])))),
                      json.dumps(self.pub, separators=(",", ":")).encode("utf-8")],                             # \\u 이스케이프
            "asof": [P.dump(dict(self.pub, asof="2026-11-06"))],
            "who": [raw],
        }
        for why, raws in bad.items():
            for i, b in enumerate(raws):
                with self.subTest(why=why, i=i):
                    keys = {"warsh", "cook"} if why == "who" else set(KEYS)
                    with self.assertRaises(P.Bad) as cm:
                        P.check_public(b, keys, TODAY)
                    self.assertEqual(cm.exception.why, why)


class RosterTest(Case):
    def test_keys_come_from_the_page_data(self):
        self.assertEqual(P.roster(self.repo), set(KEYS))
        self.assertGreaterEqual(len(P.roster(REPO)), 12)                      # 저장소의 실제 명단

    def test_unreadable_roster_stops(self):
        path = os.path.join(self.repo, "site", "people-data.js")
        for text in ("window.PEOPLE_DATA = {};\nalert(1);", "window.PEOPLE_DATA = {\"people\": []};",
                     ROSTER_JS % json.dumps({"people": [{"key": "Warsh"}]}), ROSTER_JS % json.dumps({"people": [{"name": "x"}]}), "{"):
            with self.subTest(text[:30]):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.stops("roster", P.roster, self.repo)
        os.remove(path)
        self.stops("roster", P.roster, self.repo)


class LoadTest(Case):
    def test_missing_source(self):
        e = self.stops("source", P.load, self.src, set(KEYS), TODAY)
        self.assertIsNone(e.why)

    def test_bad_source_names_the_rule(self):
        self.put_source(source([remark(venue="방송")]))
        self.assertEqual(self.stops("file", P.load, self.src, set(KEYS), TODAY).why, "venue")
        self.put_source(b"x" * (P.MAX_BYTES + 10))
        self.assertEqual(self.stops("file", P.load, self.src, set(KEYS), TODAY).why, "size")


# ---------- sync ----------

class SyncTest(Case):
    STATUS = ["git", "-c", "core.quotePath=false", "status", "--porcelain", "--untracked-files=all"]

    def test_clean_folder_goes_through_the_evening_sync(self):
        git = Tool(status=(0, ""))
        P.sync(self.repo, run=git)
        self.assertEqual(git.calls, [self.STATUS, self.STATUS, ["git", "fetch", "--quiet", "origin", "main"],
                                     ["git", "checkout", "--quiet", "--detach", "origin/main"]])

    def test_own_leftover_is_put_back_first(self):
        git = Tool(status=[(0, MOD), (0, "")])
        P.sync(self.repo, run=git)
        self.assertEqual(git.calls[1], ["git", "checkout", "--quiet", "--", PATH])
        self.assertEqual(git.names(), ["status", "checkout", "status", "fetch", "checkout"])
        self.put_published(self.public())
        git = Tool(status=[(0, NEW), (0, "")])
        P.sync(self.repo, run=git)
        self.assertFalse(os.path.exists(self.file))                          # 처음 생긴 것이면 지운다
        self.assertEqual(git.names(), ["status", "status", "fetch", "checkout"])

    def test_staged_leftover_is_unstaged(self):
        for staged, after in ((f"A  {PATH}\n", NEW), (f"M  {PATH}\n", MOD), (f"AM {PATH}\n", NEW), (f"MM {PATH}\n", MOD)):
            with self.subTest(staged):
                self.put_published(self.public())
                git = Tool(status=[(0, staged), (0, after), (0, "")])
                P.sync(self.repo, run=git)
                self.assertEqual(git.calls[1], ["git", "reset", "--quiet", "--", PATH])
                self.assertEqual(os.path.exists(self.file), after == MOD)

    def test_evening_leftover_and_ours_together(self):
        os.makedirs(os.path.join(self.repo, "data"), exist_ok=True)
        open(os.path.join(self.repo, *PICKS.split("/")), "w").close()
        git = Tool(status=[(0, MOD + f"?? {PICKS}\n"), (0, f"?? {PICKS}\n")])
        P.sync(self.repo, run=git)
        self.assertEqual(git.names(), ["status", "checkout", "status", "fetch", "checkout"])
        self.assertFalse(os.path.exists(os.path.join(self.repo, *PICKS.split("/"))))   # 저녁판 잔재는 picks_push.sync가 지운다

    def test_anything_else_is_left_alone(self):
        self.put_published(self.public())
        for out in (" M site/people.js\n", MOD + "?? note.txt\n", f"R  data/x.json -> {PATH}\n", f" D {PATH}\n", f"D  {PATH}\n",
                    " M data/people_remarks.json.bak\n", "?? .work/x\n"):
            with self.subTest(out):
                git = Tool(status=(0, out))
                self.stops("dirty", P.sync, self.repo, run=git)
                self.assertEqual(git.names(), ["status"])
        self.assertTrue(os.path.exists(self.file))
        git = Tool(status=[(0, f"M  {PATH}\n"), (0, MOD + " M site/people.js\n")])        # 풀고 보니 다른 것이 있다
        self.stops("dirty", P.sync, self.repo, run=git)
        self.assertEqual(git.names(), ["status", "reset", "status"])

    def test_git_failures_have_their_own_codes(self):
        self.stops("status", P.sync, self.repo, run=Tool(status=1))
        self.stops("fetch", P.sync, self.repo, run=Tool(status=(0, ""), fetch=1))
        self.stops("detach", P.sync, self.repo, run=Tool(status=(0, ""), checkout=1))
        self.stops("git", P.sync, self.repo, run=Tool(status=FileNotFoundError("git")))
        self.stops("status", P.sync, self.repo, run=Tool(status=[(0, f"A  {PATH}\n")], reset=1))


# ---------- 올리기 ----------

class PublishTest(Case):
    def go(self, git, doc=None):
        return P.publish(self.repo, doc or self.public(), set(KEYS), TODAY, run=git)

    def test_one_file_one_commit_one_push(self):
        git = Tool(**good())
        self.assertEqual(self.go(git), "pushed")
        self.assertEqual(git.names(), ["status", "blind", "rev-parse", "add", "commit", "rev-list", "diff", "push"])
        self.assertEqual(git.calls[3], ["git", "add", "--", PATH])
        self.assertEqual(git.calls[4], ["git", "commit", "--quiet", "-m", MSG, "--", PATH])
        self.assertEqual(git.calls[-1], PUSH)
        self.assertEqual(git.calls[1][-1].replace("\\", "/"), "scripts/check_blind.py")
        self.assertEqual(git.calls[1][1:3], ["-X", "utf8"])
        self.assertTrue(all(kw["cwd"] == self.repo for kw in git.kw))
        self.assertEqual(self.raw(), P.dump(self.public()))
        self.assertFalse(os.listdir(os.path.join(self.repo, ".work", "people_push")))   # 임시 파일이 남지 않는다

    def test_same_remarks_and_held_is_nothing_to_do(self):
        old = dict(self.public(), asof="2026-11-03")                          # asof만 다르다
        self.put_published(old)
        git = Tool(**good())
        self.assertEqual(self.go(git), "same")
        self.assertEqual(git.calls, [])
        self.assertEqual(self.raw(), P.dump(old))
        self.put_published(self.public())
        self.assertEqual(self.go(Tool(**good(status=(0, "")))), "same")

    def test_a_changed_held_or_remark_goes_up(self):
        self.put_published(dict(self.public(), held=5))
        self.assertEqual(self.go(Tool(**good(status=(0, MOD)))), "pushed")
        self.put_published(self.public(source([remark()])))
        self.assertEqual(self.go(Tool(**good(status=(0, MOD)))), "pushed")
        with open(self.file, "wb") as f:
            f.write(b"{broken")                                               # 올라 있는 파일이 깨졌으면 새로 쓴다
        self.assertEqual(self.go(Tool(**good(status=(0, MOD)))), "pushed")

    def test_another_file_in_the_tree_stops(self):
        for out in (NEW + " M data/digest.json\n", " M site/people.js\n", f"M  {PATH}\n"):
            with self.subTest(out):
                self.clear()
                git = Tool(**good(status=(0, out)))
                self.stops("scope", self.go, git)
                self.assertEqual(git.names(), ["status"])

    def test_blind_check_failure_stops_before_staging(self):
        for code in (1, 2):
            with self.subTest(code):
                self.clear()
                git = Tool(**good(blind=code))
                self.stops("blind", self.go, git)
                self.assertEqual((git.count("add"), git.count("commit"), git.count("push")), (0, 0, 0))

    def test_head_must_be_the_tip_of_main(self):
        for out in ("ccc333\naaa111\n", "aaa111\n", ""):
            with self.subTest(out):
                self.clear()
                git = Tool(**good(rev_parse=(0, out)))
                self.stops("head", self.go, git)
                self.assertEqual(git.count("add"), 0)

    def test_commit_failure_unstages(self):
        for fail in ("add", "commit"):
            with self.subTest(fail):
                self.clear()
                git = Tool(**good(**{fail: 1}))
                self.stops("commit", self.go, git)
                self.assertEqual(git.calls[-1], ["git", "reset", "--quiet", "--", PATH])
                self.assertEqual(git.count("push"), 0)

    def test_commit_must_be_one_with_one_file(self):
        for more in ({"rev_list": (0, "2\n")}, {"diff": (0, PATH + "\ndata/digest.json\n")}, {"diff": (0, "")}, {"rev_list": (1, "")}):
            with self.subTest(more):
                self.clear()
                git = Tool(**good(**more))
                self.stops("commits", self.go, git)
                self.assertEqual(git.count("push"), 0)

    def test_written_file_is_checked_again(self):
        doc = self.public()
        real = P._write

        def tamper(repo, raw):
            real(repo, raw + b" ")
        with mock.patch.object(P, "_write", tamper):
            self.assertEqual(self.stops("file", self.go, Tool(**good()), doc).why, "written")

    def test_push_refused_while_main_stood_still(self):
        git = Tool(**good(push=1))
        self.stops("push", self.go, git)
        self.assertEqual((git.count("push"), git.count("checkout")), (1, 0))


class MovedMainTest(Case):
    def moved(self, roster=None, published=None, **more):
        """첫 push가 거절되고 main이 움직였다. 새 main으로 옮기면 파일 · 명단이 그쪽 것이 된다."""
        def checkout(cmd):
            if "--detach" in cmd:
                if published is None:
                    os.remove(self.file)
                else:
                    self.put_published(published)
                if roster is not None:
                    self.put_roster(roster)
            return 0
        return Tool(**{**good(rev_parse=[(0, "aaa111\naaa111\n"), (0, "bbb222\n")], push=[1, 0], checkout=checkout), **more})

    def go(self, git):
        return P.publish(self.repo, self.public(), set(KEYS), TODAY, run=git)

    def test_same_bytes_go_up_on_the_new_main(self):
        git = self.moved()
        self.assertEqual(self.go(git), "pushed")
        self.assertEqual(git.names(), ["status", "blind", "rev-parse", "add", "commit", "rev-list", "diff", "push",
                                       "fetch", "rev-parse", "checkout", "status", "add", "commit", "rev-list", "diff", "push"])
        self.assertEqual(git.calls[10], ["git", "checkout", "--quiet", "--detach", "origin/main"])
        self.assertEqual(self.raw(), P.dump(self.public()))
        self.assertEqual(git.count("blind"), 1)

    def test_a_person_dropped_from_the_new_roster_stops(self):
        git = self.moved(roster=("warsh", "hammack"))
        self.stops("moved", self.go, git)
        self.assertEqual((git.count("push"), git.count("commit")), (1, 1))
        self.put_roster(KEYS)
        self.clear()
        git = self.moved(roster=())                                          # 명단을 읽을 수 없게 됐다
        self.stops("moved", self.go, git)

    def test_new_main_already_has_it(self):
        git = self.moved(published=dict(self.public(), asof="2026-11-03"))
        self.assertEqual(self.go(git), "same")
        self.assertEqual(git.count("push"), 1)

    def test_only_one_more_try(self):
        git = self.moved(push=1)
        self.stops("push", self.go, git)
        self.assertEqual(git.count("push"), 2)

    def test_scope_and_commits_are_checked_again(self):
        self.stops("commits", self.go, self.moved(rev_list=[(0, "1\n"), (0, "2\n")]))
        self.clear()
        self.stops("scope", self.go, self.moved(status=[(0, NEW), (0, NEW + " M data/digest.json\n")]))
        self.clear()
        self.stops("fetch", self.go, Tool(**good(push=1, fetch=1)))


# ---------- 한 번에 돌리기 · 정리 · 로그 ----------

class MainTest(Case):
    def setUp(self):
        super().setUp()
        self.log = os.path.join(self.repo, "..", os.path.basename(self.repo) + "-people-push.log")
        self.addCleanup(lambda: os.path.exists(self.log) and os.remove(self.log))

    def main(self, git, *extra, today=TODAY):
        out = io.StringIO()
        with redirect_stdout(out):
            code = P.main(["--repo-dir", self.repo, "--source", self.src, "--log", self.log, *extra], run=git, python="py",
                          today=today, now=lambda: datetime.datetime(2026, 11, 4, 17, 50, tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
        self.out = out.getvalue()
        return code

    def logged(self):
        with open(self.log, encoding="utf-8") as f:
            return f.read().splitlines()

    def flow(self, **more):
        """sync(깨끗한 폴더) → 쓰기 뒤 새 파일 한 줄 → 나머지는 good()."""
        return Tool(**good(status=[(0, ""), (0, ""), (0, NEW), (0, NEW)], **more))

    def test_pushed_run_logs_one_line_of_counts(self):
        self.put_source(source())
        git = self.flow()
        self.assertEqual(self.main(git), 0)
        self.assertEqual(git.names()[:4], ["status", "status", "fetch", "checkout"])
        self.assertEqual(git.count("push"), 1)
        lines = self.logged()
        self.assertEqual(lines, ["2026-11-04T17:50:00+09:00 [people_push] run code=ok result=pushed asof=2026-11-04 remarks=3 held=2 people=3"])
        self.assertIn(lines[0], self.out)

    def test_same_run(self):
        self.put_source(source())
        self.put_published(dict(self.public(), asof="2026-11-01"))
        git = Tool(status=(0, ""))
        self.assertEqual(self.main(git), 0)
        self.assertEqual(git.names(), ["status", "status", "fetch", "checkout"])
        self.assertIn("result=same", self.logged()[0])

    def test_missing_source_changes_nothing(self):
        git = Tool(status=(0, ""))
        self.assertEqual(self.main(git), 2)
        self.assertEqual(git.names(), ["status", "status", "fetch", "checkout", "reset", "status"])   # 옮기고 정리만
        self.assertFalse(os.path.exists(self.file))
        self.assertTrue(self.logged()[0].endswith("[people_push] run code=source"))

    def test_bad_source_logs_the_rule_not_the_text(self):
        self.put_source(source([remark(topic=CANARY + "가" * 40)]))
        self.assertEqual(self.main(Tool(status=(0, ""))), 2)
        self.assertTrue(self.logged()[0].endswith("run code=file why=topic"))
        self.assertFalse(os.path.exists(self.file))
        self.assertNotIn(CANARY, self.out)

    def test_failure_after_writing_leaves_the_folder_clean(self):
        """공개 전 검사 · 머리 · 커밋 · 푸시 어디서 멈춰도 발언 파일을 되돌린다 — 저녁판 sync가 다음 실행에서 dirty로 막히지 않게."""
        for name, more in {"blind": {"blind": 1}, "head": {"rev_parse": (0, "x\ny\n")}, "commit": {"commit": 1},
                           "push": {"push": 1}}.items():
            with self.subTest(name):
                self.put_source(source())
                git = self.flow(**more)
                self.assertEqual(self.main(git), 2)
                self.assertFalse(os.path.exists(self.file), name)             # 새 파일이었으니 지운다
                self.assertIn(["git", "reset", "--quiet", "--", PATH], git.calls)
                self.assertTrue(self.logged()[-1].endswith(f"code={name}"))
        self.put_published(dict(self.public(), held=9))
        git = Tool(**good(status=[(0, ""), (0, ""), (0, MOD), (0, MOD)], blind=1))
        self.assertEqual(self.main(git), 2)
        self.assertEqual(git.calls[-1], ["git", "checkout", "--quiet", "--", PATH])   # 고쳐진 것이면 HEAD의 것으로

    def test_unexpected_failure_is_exit_one_and_still_tidies(self):
        self.put_source(source())
        git = self.flow(add=RuntimeError(CANARY))
        self.assertEqual(self.main(git), 1)
        self.assertFalse(os.path.exists(self.file))
        self.assertTrue(self.logged()[-1].endswith("code=error kind=RuntimeError"))
        self.assertNotIn(CANARY, "\n".join(self.logged()) + self.out)

    def test_dirty_folder_is_not_touched(self):
        self.put_source(source())
        self.put_published(self.public())
        git = Tool(status=(0, MOD + " M site/people.js\n"))
        self.assertEqual(self.main(git), 2)
        self.assertEqual(git.names(), ["status"])
        self.assertTrue(os.path.exists(self.file))
        self.assertTrue(self.logged()[0].endswith("code=dirty"))

    def test_log_never_carries_file_text(self):
        self.put_source(source([remark(topic=CANARY, why=CANARY, quote=CANARY)]))
        self.main(self.flow())
        self.main(Tool(status=(0, "")))
        for line in self.logged():
            self.assertNotIn(CANARY, line)
            self.assertRegex(line, r"^\S+ \[people_push\] run( [a-z]+=[\w:+-]+)+$")
        note_log = os.path.join(self.repo, "note.log")
        P.note(note_log, "t", code="ok", topic=CANARY, why="has space", n=3, flag=True)
        with open(note_log, encoding="utf-8") as f:
            self.assertEqual(f.read(), "t [people_push] run code=ok topic=(hidden) why=(hidden) n=3 flag=true\n")

    def test_default_log_is_in_the_user_folder(self):
        with mock.patch.dict(os.environ, {"HOME": self.repo, "USERPROFILE": self.repo}):
            a = P.parse(["--repo-dir", self.repo, "--source", self.src])
            self.assertEqual(P.log_path(a), os.path.join(self.repo, ".macro-notes", "people-push.log"))
            a = P.parse(["--repo-dir", self.repo, "--source", self.src, "--dry-run"])
            self.assertEqual(P.log_path(a), os.path.join(self.repo, ".work", "people_dry", "people-push.log"))

    def test_dry_run_needs_no_git(self):
        self.put_source(source())
        git = Tool(status=1)
        self.assertEqual(self.main(git, "--dry-run"), 0)
        self.assertEqual(git.calls, [])
        out = os.path.join(self.repo, ".work", "people_dry", "people_remarks.json")
        with open(out, "rb") as f:
            self.assertEqual(f.read(), P.dump(self.public()))
        self.assertIn(out, self.out)
        self.assertFalse(os.path.exists(self.file))
        self.assertIn("result=dry", self.logged()[0])
        self.put_source(source([remark(venue="방송")]))
        os.remove(out)
        self.assertEqual(self.main(git, "--dry-run"), 2)
        self.assertFalse(os.path.exists(out))
        self.assertEqual(git.calls, [])

    def test_cli_exit_codes(self):
        self.put_source(source())
        r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "people_push.py"), "--repo-dir", self.repo, "--source",
                            self.src, "--dry-run", "--log", self.log], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "people_push.py"), "--repo-dir", self.repo, "--source",
                            self.src + ".none", "--dry-run", "--log", self.log], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "people_push.py")], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 2)                                     # argparse 사용법 오류


# ---------- 진짜 git ----------

@unittest.skipUnless(shutil.which("git"), "git이 없다")
class RealGitTest(unittest.TestCase):
    """임시 폴더의 진짜 git — 원격은 그 안의 bare 저장소. 공개 전 검사만 가짜(blind 값이 종료코드)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.origin, self.pc, self.other = (os.path.join(self.tmp, n) for n in ("origin.git", "pc", "other"))
        self.git(self.tmp, "init", "--quiet", "--bare", "--initial-branch=main", self.origin)
        for repo in (self.pc, self.other):
            self.git(self.tmp, "clone", "--quiet", self.origin, repo)
            for k, v in (("user.name", "fx"), ("user.email", "fx@example.invalid"), ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
                self.git(repo, "config", k, v)
        self.roster(self.other, KEYS)
        with open(os.path.join(self.other, *PICKS.split("/")), "w", encoding="utf-8") as f:
            f.write("{}")
        with open(os.path.join(self.other, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(".work/\n")
        self.commit(self.other, "seed")
        self.git(self.pc, "fetch", "--quiet", "origin", "main")
        self.git(self.pc, "checkout", "--quiet", "--detach", "origin/main")
        self.src = os.path.join(self.tmp, "people-remarks.json")
        self.file = os.path.join(self.pc, *PATH.split("/"))
        self.blind = 0

    def git(self, cwd, *args):
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=120)
        self.assertEqual(r.returncode, 0, (args[:2], r.stderr[-300:]))
        return r.stdout.decode("utf-8", "replace")

    def roster(self, repo, keys):
        os.makedirs(os.path.join(repo, "site"), exist_ok=True)
        os.makedirs(os.path.join(repo, "data"), exist_ok=True)
        with open(os.path.join(repo, "site", "people-data.js"), "w", encoding="utf-8") as f:
            f.write(ROSTER_JS % json.dumps({"people": [{"key": k} for k in keys]}))

    def commit(self, repo, message):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "--quiet", "-m", message)
        self.git(repo, "push", "--quiet", "origin", "HEAD:main")

    def tool(self, cmd, **kw):
        if cmd[0] != "git":
            return subprocess.CompletedProcess(cmd, self.blind, b"", b"")
        return subprocess.run(cmd, **kw)

    def run_main(self, doc):
        with open(self.src, "wb") as f:
            f.write(enc(doc))
        with redirect_stdout(io.StringIO()):
            return P.main(["--repo-dir", self.pc, "--source", self.src, "--log", os.path.join(self.tmp, "push.log")],
                          run=self.tool, python=sys.executable, today=TODAY)

    def on_main(self):
        self.git(self.other, "fetch", "--quiet", "origin", "main")
        return self.git(self.other, "show", f"origin/main:{PATH}").encode("utf-8")

    def status(self, repo=None):
        return self.git(repo or self.pc, "status", "--porcelain", "--untracked-files=all")

    def public(self, doc):
        return P.dump(P.check_source(enc(doc), set(KEYS), TODAY))

    def test_first_upload_then_same_then_a_change(self):
        self.assertEqual(self.run_main(source()), 0)
        self.assertEqual(self.on_main(), self.public(source()))
        self.assertEqual(self.git(self.other, "log", "-1", "--format=%s", "origin/main").strip(), MSG)
        self.assertEqual(self.git(self.other, "diff", "--name-only", "origin/main~1", "origin/main").strip(), PATH)
        count = self.git(self.other, "rev-list", "--count", "origin/main").strip()
        self.assertEqual(self.run_main(source(generated_at="2026-11-05T08:00:00+09:00", window_from="2025-11-05")), 0)   # asof만 다르다
        self.assertEqual(self.git(self.other, "rev-list", "--count", "origin/main").strip(), count)
        self.assertEqual(self.run_main(source(held=7)), 0)
        self.assertEqual(json.loads(self.on_main())["held"], 7)
        self.assertEqual(self.status(), "")

    def test_leftovers_of_both_publishers_are_cleaned(self):
        self.assertEqual(self.run_main(source()), 0)
        with open(self.file, "wb") as f:
            f.write(b"{}")
        self.git(self.pc, "add", "--", PATH)                                  # 커밋 직전에 끊긴 실행
        with open(os.path.join(self.pc, *PICKS.split("/")), "w", encoding="utf-8") as f:
            f.write('{"x":1}')                                                # 저녁판이 올리지 못하고 남긴 것
        P.sync(self.pc, run=self.tool)
        self.assertEqual(self.status(), "")
        self.assertEqual(open(self.file, "rb").read(), self.public(source()))

    def test_failure_leaves_the_folder_ready_for_the_evening_sync(self):
        PP = P._picks()
        self.blind = 1
        self.assertEqual(self.run_main(source()), 2)
        self.assertEqual(self.status(), "")
        self.assertFalse(os.path.exists(self.file))
        PP.sync(self.pc, run=self.tool)                                       # 저녁판은 막히지 않는다
        self.blind = 0
        self.assertEqual(self.run_main(source()), 0)
        self.assertEqual(self.run_main(source(held=3)), 0)
        self.blind = 1
        self.assertEqual(self.run_main(source(held=4)), 2)                    # 고쳐진 파일이면 main의 것으로 되돌린다
        self.assertEqual(self.status(), "")
        self.assertEqual(json.loads(open(self.file, "rb").read())["held"], 3)

    def test_an_unrelated_commit_on_main_is_followed(self):
        self.git(self.pc, "fetch", "--quiet", "origin", "main")
        orig = P.sync

        def stale_sync(repo, run):
            orig(repo, run)
            with open(os.path.join(self.other, "data", "calendar.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            self.commit(self.other, "other")                                  # sync가 끝난 뒤 main이 움직였다
        with mock.patch.object(P, "sync", stale_sync):
            self.assertEqual(self.run_main(source()), 0)
        self.assertEqual(self.on_main(), self.public(source()))
        self.assertEqual(self.git(self.other, "diff", "--name-only", "origin/main~1", "origin/main").strip(), PATH)

    def test_a_dropped_person_on_the_new_main_is_not_published(self):
        orig = P.sync

        def stale_sync(repo, run):
            orig(repo, run)
            self.roster(self.other, ("warsh", "hammack"))
            self.commit(self.other, "roster")
        with mock.patch.object(P, "sync", stale_sync):
            self.assertEqual(self.run_main(source()), 2)
        self.assertEqual(self.status(), "")
        self.git(self.other, "fetch", "--quiet", "origin", "main")
        self.assertNotIn(PATH, self.git(self.other, "ls-tree", "-r", "--name-only", "origin/main"))


# ---------- 저장소의 공개 파일 ----------

DATA_FILE = os.path.join(REPO, *PATH.split("/"))


def file_keys(raw, roster):
    """CI가 올라 있는 공개 파일을 볼 때 쓰는 명단 = 지금 명단 ∪ 파일에 든 꼴 맞는 사람 key.
    명단에서 사람을 뺀 커밋(매년 1월 교대 · 임시 총재 후임)이 그 사람의 옛 발언 때문에 check를 떨어뜨려 아침 갱신 · 배포를 통째로 막지
    않게(2026-11-04 검토 push-1) — 화면(people.js)은 명단 밖 사람의 발언을 하나씩 건너뛰고, 명단 검사는 게시기(people_push.load ·
    publish)가 올릴 때 그대로 한다. 꼴(소문자 key) · 그 밖의 약속은 여기서도 다 본다."""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return set(roster)
    rs = doc.get("remarks") if type(doc) is dict else None
    found = {r["who"] for r in (rs if type(rs) is list else []) if type(r) is dict and type(r.get("who")) is str
             and P.KEY_RE.fullmatch(r["who"])}
    return set(roster) | found


@unittest.skipUnless(os.path.exists(DATA_FILE), "data/people_remarks.json이 아직 없다")
class DataFileTest(unittest.TestCase):
    """올라 있는 공개 파일을 게시기와 같은 검사로 — 손으로 고쳐 깨뜨린 파일이 배포되지 않게(CI의 check가 배포 앞에서 돈다).
    명단만은 보지 않는다(file_keys — 명단에서 빠진 사람의 발언은 화면이 건너뛴다)."""

    def test_published_file_follows_the_contract(self):
        with open(DATA_FILE, "rb") as f:
            raw = f.read()
        doc = P.check_public(raw, file_keys(raw, P.roster(REPO)), datetime.date.today())
        self.assertEqual(list(doc), list(P.PUBLIC_KEYS))


class RosterRemovalTest(unittest.TestCase):
    """명단에서 사람을 빼도 CI의 파일 검사는 떨어지지 않고(그 사람의 옛 발언은 화면이 건너뛴다), 게시기는 여전히 명단으로 막는다."""

    def setUp(self):
        self.raw = P.dump(P.check_source(enc(source()), set(KEYS), TODAY))
        self.fewer = {"warsh", "hammack"}                                      # cook을 명단에서 뺐다

    def test_the_ci_file_check_ignores_the_roster_but_not_the_contract(self):
        self.assertRaises(P.Bad, P.check_public, self.raw, self.fewer, TODAY)  # 명단으로 보면 떨어지던 것(재현)
        doc = P.check_public(self.raw, file_keys(self.raw, self.fewer), TODAY)
        self.assertEqual({r["who"] for r in doc["remarks"]}, set(KEYS))
        for bad in (self.raw.replace(b'"held":2', b'"held":-1'), self.raw.replace(b'"who":"cook"', b'"who":"Cook"'),
                    self.raw.replace(b'"who":"cook"', b'"who":"nobody"'), self.raw[:-1], b"[]", b"\xff"):
            with self.subTest(bad=bad[:40]):                                    # 그 밖의 약속(꼴 · id 규칙 · 바이트)은 그대로 본다
                self.assertRaises(P.Bad, P.check_public, bad, file_keys(bad, self.fewer), TODAY)
        self.assertEqual(file_keys(b"{", self.fewer), self.fewer)

    def test_the_publisher_still_refuses_a_person_off_the_roster(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        src = os.path.join(tmp, "source.json")
        with open(src, "wb") as f:
            f.write(enc(source()))
        with self.assertRaises(P.Stop) as e:
            P.load(src, self.fewer, TODAY)
        self.assertEqual((e.exception.code, e.exception.why), ("file", "who"))


# ---------- 아침 워크플로의 배포 문 ----------

def deploy_job():
    """daily.yml의 deploy 잡 글 — (잡 글, 단계 목록[각 단계의 글])."""
    with open(os.path.join(REPO, ".github", "workflows", "daily.yml"), encoding="utf-8") as f:
        wf = f.read()
    job = wf[wf.index("\n  deploy:\n"):wf.index("\n  alert:\n")]
    steps = re.split(r"\n(?=      - )", job[job.index("    steps:\n") + len("    steps:\n"):])
    return job, [s for s in steps if s.strip()]


def gate_script():
    """'main이 앞서 나갔는지' 단계의 run 글(들여쓰기를 뗀 셸 글)."""
    _, steps = deploy_job()
    step = next(s for s in steps if "id: tip" in s)
    body = step[step.index("run: |\n") + len("run: |\n"):]
    return "\n".join(line[10:] for line in body.split("\n"))


class DeployGateTest(unittest.TestCase):
    """PC의 push(연준 인물 · 저녁판 AI 요약)가 아침 예약 실행과 겹칠 때 — 기다리던 push 실행이 봇 커밋 뒤에 옛 커밋을 다시 배포하지
    않는다(2026-11-04 검토 push-4). push 실행만 main의 끝을 다시 받아, 앞서 나갔으면 배포 셋을 건너뛴다. 예약 · 수동은 그대로."""

    def test_the_gate_is_push_only_and_guards_the_three_deploy_steps(self):
        job, steps = deploy_job()
        names = [("checkout" if "actions/checkout@" in s else "tip" if "id: tip" in s else "assemble" if "사이트 조립" in s
                  else "configure" if "configure-pages@" in s else "upload" if "upload-pages-artifact@" in s
                  else "deploy" if "deploy-pages@" in s else "?") for s in steps]
        self.assertEqual(names, ["checkout", "tip", "assemble", "configure", "upload", "deploy"])
        tip = steps[1]
        self.assertIn("        if: github.event_name == 'push'", tip.split("\n"))              # 예약 · 수동 실행은 이 단계를 건너뛴다 → 그대로 배포
        for s in steps[3:]:
            self.assertIn("        if: steps.tip.outputs.newer != 'true'", s.split("\n"))       # 건너뛴 단계의 출력은 비어 있다 → != 'true'
        for s in steps[:3]:
            self.assertNotIn("steps.tip.outputs", s)
        self.assertIn("ref: ${{ needs.update.outputs.sha || github.sha }}", steps[0])  # 배포하는 것은 여전히 검사를 거친 그 커밋
        self.assertIn("always() && needs.check.result == 'success' &&", job)
        self.assertIn("(github.event_name == 'push' || needs.update.outputs.publish == 'true')", job)
        script = gate_script()
        self.assertNotIn("${{", script)                                              # 셸에는 표현식을 넣지 않는다(GITHUB_SHA는 러너의 환경)
        self.assertIn("git fetch --quiet --no-tags --depth=1 origin main", script)
        self.assertIn('"$GITHUB_SHA"', script)

    def run_gate(self, cwd, sha):
        out = os.path.join(self.tmp, "out")
        open(out, "w").close()
        r = subprocess.run(["bash", "-e", "-c", gate_script()], cwd=cwd, capture_output=True, timeout=60,
                           env={**os.environ, "GITHUB_SHA": sha, "GITHUB_OUTPUT": out, "GIT_TERMINAL_PROMPT": "0"})
        with open(out, encoding="utf-8") as f:
            return r.returncode, f.read(), r.stdout.decode("utf-8", "replace")

    @unittest.skipUnless(shutil.which("git") and shutil.which("bash"), "git · bash가 없다")
    def test_the_gate_with_real_git(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        origin, seed, run = (os.path.join(self.tmp, n) for n in ("origin.git", "seed", "run"))

        def git(cwd, *args):
            r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=60)
            self.assertEqual(r.returncode, 0, (args[:2], r.stderr[-300:]))
            return r.stdout.decode("utf-8").strip()
        git(self.tmp, "init", "--quiet", "--bare", "--initial-branch=main", origin)
        git(self.tmp, "clone", "--quiet", origin, seed)
        for k, v in (("user.name", "fx"), ("user.email", "fx@example.invalid"), ("commit.gpgsign", "false")):
            git(seed, "config", k, v)

        def push(msg):
            git(seed, "commit", "--quiet", "--allow-empty", "-m", msg)
            git(seed, "push", "--quiet", "origin", "HEAD:main")
            return git(seed, "rev-parse", "HEAD")
        a = push("people commit")
        git(self.tmp, "clone", "--quiet", "--depth=1", "file://" + origin, run)          # 러너의 얕은 checkout처럼
        self.assertEqual(self.run_gate(run, a)[:2], (0, "newer=false\n"))              # main = 이 커밋 → 배포
        b = push("data: bot commit")
        code, out, said = self.run_gate(run, a)
        self.assertEqual((code, out), (0, "newer=true\n"))                             # 기다리는 사이 봇 커밋이 들어왔다 → 건너뜀
        self.assertIn("::notice::", said)
        self.assertIn(b, said)
        self.assertEqual(self.run_gate(run, b)[:2], (0, "newer=false\n"))
        git(run, "remote", "set-url", "origin", os.path.join(self.tmp, "nowhere.git"))
        code, out, said = self.run_gate(run, a)
        self.assertEqual((code, out), (0, "newer=false\n"))                            # 끝을 받지 못하면 그대로 배포(지금까지처럼)
        self.assertIn("::warning::", said)


class TakedownTest(unittest.TestCase):
    """README '보류 · 내리기'의 칸 전체 내리기(두 파일을 main에서 지움)가 아침 검사를 떨어뜨리지 않는가 — 떨어지면 내리는 push가
    배포되지 않고(발언 · 인용이 남는다) 그 뒤 예약 갱신도 check에서 멈춘다(audit 2026-11-10 c-pub-repo-01). 임시 폴더의 사본에서
    게시기를 import하는 두 테스트 파일을 따로 돌린다(사본에는 게시기가 없으니 이 묶음은 거기서 다시 돌지 않는다)."""

    def copy(self, keep_data):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "scripts"))
        for name in ("test_people_push.py", "test_people_site.py", "test_people_render.cjs"):
            shutil.copy(os.path.join(HERE, name), os.path.join(tmp, "scripts", name))
        shutil.copytree(os.path.join(REPO, "site"), os.path.join(tmp, "site"))
        shutil.copy(os.path.join(REPO, "README.md"), os.path.join(tmp, "README.md"))
        os.makedirs(os.path.join(tmp, ".github", "workflows"))
        shutil.copy(os.path.join(REPO, ".github", "workflows", "daily.yml"), os.path.join(tmp, ".github", "workflows", "daily.yml"))
        os.makedirs(os.path.join(tmp, "data"))
        if keep_data:
            with open(os.path.join(tmp, *PATH.split("/")), "wb") as f:
                f.write(P.dump(P.check_source(enc(source()), set(KEYS), TODAY)))
        return tmp

    def discover(self, tmp, pattern):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "scripts", "-p", pattern],
                           cwd=tmp, capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
        return r.returncode, r.stdout + r.stderr

    def test_only_the_two_guarded_files_import_the_publisher(self):
        users = set()
        for d in (HERE, os.path.join(HERE, "evening")):
            for name in os.listdir(d):
                if name.endswith(".py") and name != "people_push.py":
                    with open(os.path.join(d, name), encoding="utf-8") as f:
                        if re.search(r"^\s*(import|from)\s+people_push\b", f.read(), flags=re.M):
                            users.add(name)
        self.assertEqual(users, {"test_people_push.py", "test_people_site.py"})   # 새로 import하는 곳은 같은 가드를 단다

    def test_removing_both_files_keeps_the_check_green(self):
        code, out = self.discover(self.copy(keep_data=False), "test_people_*.py")
        self.assertEqual(code, 0, out[-2000:])
        self.assertRegex(out, r"OK \(skipped=\d+\)")
        self.assertNotIn("ERROR", out)

    def test_removing_only_the_publisher_still_fails(self):
        code, out = self.discover(self.copy(keep_data=True), "test_people_push.py")   # 올라 있는 파일을 검사할 길이 없다
        self.assertNotEqual(code, 0)
        self.assertIn("data/people_remarks.json이 남아 있다", out)


class ReadmeTest(unittest.TestCase):
    def test_readme_counts_and_section(self):
        with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part = m.group(3).split(" / node: ")[0]
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )연준 인물 게시 {mine}( · |$)")
        self.assertIn("python -X utf8 scripts/test_people_push.py", readme)
        sec = readme[readme.index("### 연준 인물 — 새 발언 자동 분류"):]
        sec = sec[:sec.index("\n## ")]
        for word in ("people_push.py", "data/people_remarks.json", "agree", "15단어", "예측이 아닙니다", "Evening-Summary.ps1",
                     "자동 분류", "people-remarks.json", "people-push.log"):
            self.assertIn(word, sec, word)


if __name__ == "__main__":
    unittest.main()
