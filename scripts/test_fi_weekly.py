#!/usr/bin/env python3
"""평가사 주간 보고서(fi_weekly) 테스트 — 목록 · 표 · 요약 쪽을 약속대로 읽는가, 요약을 검사하는가, 그 파일 하나만 올리는가,
멈추면 폴더를 깨끗이 두는가, 화면과 약속이 같은가.

실행:  python -X utf8 scripts/test_fi_weekly.py   (아침 묶음 `python -m unittest discover -s scripts`가 함께 돈다)
네트워크 불필요 — 받기는 가짜 수신기(주소 → 바이트), PDF는 가짜 쪽 읽기(바이트 → 쪽 글), claude는 가짜 실행기, git은 가짜 실행기이고
끝의 묶음만 임시 폴더의 진짜 git으로 돈다. 보고서의 글 · 숫자 · 호수 · 글 번호는 모두 지어낸 것이다(실제 보고서를 담지 않는다).
끝의 DataFileTest는 저장소에 data/fi_weekly.json이 있으면 그 파일을 게시기와 같은 검사로 본다(CI가 배포 전에).
칸을 내려 scripts/fi_weekly.py를 지운 저장소에서는 묶음 전체를 건너뛴다(공개 파일까지 지웠을 때만).
"""
import datetime
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
import urllib.error
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_FILE = os.path.join(REPO, "data", "fi_weekly.json")
sys.path.insert(0, HERE)
if not os.path.exists(os.path.join(HERE, "fi_weekly.py")):
    if os.path.exists(DATA_FILE):
        raise ImportError("scripts/fi_weekly.py가 없는데 data/fi_weekly.json이 남아 있다 — 칸을 내릴 때는 두 파일을 함께 지운다")
    raise unittest.SkipTest("scripts/fi_weekly.py를 지웠다(평가사 주간 보고서 칸을 내림)")
import fi_weekly as F

K, R, L = F._evening()
TODAY = datetime.date(2026, 11, 17)
KST = datetime.timezone(datetime.timedelta(hours=9))
PATH = "data/fi_weekly.json"
NEW, MOD = f"?? {PATH}\n", f" M {PATH}\n"
CANARY = "카나리아요약zq"                     # 요약 글 — 로그 · 출력 어디에도 나오면 안 된다


# ---------- 지어낸 보고서 ----------

def swap_block(no, caption, label, this, prev, rows):
    """SWAP 절의 표 하나(layout 꼴) — rows = {만기: (이번 주, 지난주, 지난해 말)}. 주간증감 · 연말대비는 계산해 넣는다."""
    ten = list(rows)
    ye = f"{int(this[:4]) - 1}-12-31"
    fmt = lambda v: f"{v:.4f}".rstrip("0").rstrip(".")
    out = [f"표{no}. {caption}                                (단위: %, BP)", f"       {label}      " + "      ".join(ten)]
    out.append(f"      {this}    " + "    ".join(fmt(rows[t][0]) for t in ten))
    out.append(f"      {prev}    " + "    ".join(fmt(rows[t][1]) for t in ten))
    out.append("       주간증감     " + "    ".join(fmt(round(rows[t][0] - rows[t][1], 4)) for t in ten))
    out.append(f"      {ye}    " + "    ".join(fmt(rows[t][2]) for t in ten))
    out.append("       연말대비     " + "    ".join(fmt(round(rows[t][0] - rows[t][2], 4)) for t in ten))
    out.append("자료 : KIS자산평가")
    return "\n".join(out)


IRS = {"1Y": (3.10, 3.00, 2.50), "2Y": (3.20, 3.05, 2.60), "3Y": (3.3025, 3.15, 2.70), "5Y": (3.40, 3.30, 2.90)}
CRS = {"1Y": (2.90, 2.85, 2.20), "2Y": (2.95, 2.90, 2.30), "3Y": (3.00, 2.92, 2.40), "5Y": (3.05, 3.00, 2.60)}
KTB = {"1Y": (3.12, 3.03, 2.40), "2Y": (3.21, 3.10, 2.55), "3Y": (3.29, 3.16, 2.70), "5Y": (3.38, 3.27, 2.95)}
GRADE_ROWS = {"AAA": [50.0, 45.0, 40.0, 50.0, -1.0, 0.5, 1.0, 0.0, 0.5, 0.3, 4.0, 0.0],
              "AA+": [60.0, 55.0, 50.0, 80.0, -1.0, -0.5, 1.0, 0.0, -0.7, -0.7, 4.2, 0.0],
              "AA0": [64.0, 60.0, 57.0, 110.0, -1.0, -0.5, 1.0, 0.0, -0.7, -0.7, 4.0, 0.0],
              "AA-": [68.0, 65.0, 66.0, 150.0, -1.0, -0.7, 1.0, 0.0, -0.7, -0.7, 3.8, 0.0],
              "A+": [86.0, 105.0, 130.0, 200.0, -2.0, -0.5, 1.0, 0.0, 1.5, -0.5, 3.8, 0.0],
              "A0": [100.0, 130.0, 175.0, 250.0, -2.0, -0.5, 1.0, 0.0, 1.5, 0.0, 3.8, 0.0],
              "A-": [128.0, 175.0, 235.0, 300.0, -2.0, 1.2, 1.0, 0.0, 1.5, 0.0, 3.8, 0.0]}


def credit_block(this="11/13", prev="11/06", rows=None, minus="-"):
    rows = GRADE_ROWS if rows is None else rows
    out = ["표1. 크레딧 스프레드 및 변동폭                                      (단위: bp)",
           f"       등급              금주 스프레드({this})              전주대비({prev})               전월대비(10/16)",
           "       만기            " + "     ".join(["1Y", "3Y", "5Y", "10Y"] * 3)]
    for g, v in rows.items():
        out.append(f"       {g.replace('-', minus)}          " + "   ".join(f"{x:.1f}".replace("-", minus) for x in v))
    out.append("자료 : KIS자산평가")
    return "\n".join(out)


EXEC = """Executive Summary



INDEX       지어낸 채권지수 추이
             • 지어낸 지수 누적수익률 감소
국공채         지어낸 대외 금리 상승에 따른 약세
             • 지어낸 물가 지표 예상치 상회
             • 지어낸 인사 매파적 발언 주목
금융채         크레딧 약세 지속
             • 은행채 스프레드 축소 및 강세
회사채         회사채 금리 전구간 상승
             • 회사채 커브 플래트닝
             • 회사채 스프레드 단기구간 축소
ABS/MBS     가나다라제일차유동화 발행
             • 가나다라제일차유동화 발행
CD/CP       CD 시장 발행 감소
             • CD : 감소, CD-은행채 스프레드 감소
해외채권        지어낸 물가 우려에 미 국채금리
             상승
             • 지어낸 유가 반등이 인플레이션 우려 자극
ELS         지어낸 주가지수 마감
             • 지어낸 주가지수 상승
SWAP        CD 91일물 금리 0.03% 상승
             • IRS 금리 상승세, CRS 금리 상승세
             • SWAP SPREAD 상승세, SWAP BASIS 하락세
                                    2
"""
MARKET = """국공채 : 지어낸 대외 금리 상승에 따른 약세

평가담당자                    KEY POINT

홍길동 과장     02) 1234-5678 •  지어낸 물가 지표 예상치 상회

  I.  시장동향 및 금리변동

    주 첫 영업일 국내 채권시장은 지어낸 증시 호조에 약세로 출발했고, 주중 지어낸 물가 지표가 예상치를 상회하며 금리가

상승했다. 국고 3년물은 지난주 대비 12.5bp 상승했고 국고 10년은 14.0bp 상승 마감했다. 문의는 someone@example.invalid

그림1. 국고채 금리변동                  (단위 : %)
"""


def kis_pages(issue="1212", date="2026-11-13", prev="2026-11-06", irs=IRS, crs=CRS, ktb=KTB, credit=None, extra=()):
    d = datetime.date.fromisoformat(date)
    cover = f"KIS WEEKLY                   {issue}호 {d.strftime('%Y.%m.%d')}\n\n PART  1 국내  / 해외채권\n"
    credit = credit if credit is not None else credit_block(f"{d.month}/{d.day}", f"{int(prev[5:7])}/{int(prev[8:])}")
    swap1 = swap_block(2, "KRW IRS Data", "KRW IRS", date, prev, irs) + "\n\n그림5. KRW CRS\n\n" + swap_block(3, "KRW CRS Data", "KRW CRS", date, prev, crs)
    swap2 = swap_block(4, "KTB Data", "URD IRS", date, prev, ktb) + "\n\n그림7. IRS 장단기 스프레드 추이\n"
    return [cover, EXEC, MARKET, "회사채 : 지어낸 제목\n\n" + credit + "\n\n                18\n", swap1, swap2, *extra]


KAP_PAGE = """Fixed Income Weekly
November 16, Vol.26-46



Summary

 (%) 주간변동 2026-11-06 2026-11-13 (bp)
 4.700 2.3 5.0
 3개월 1년 2년 3년 5년 10년 20년 30년
▲ 수익률곡선추이와장단기금리등락폭


   지어낸 단기 금리는 연말 차환 부담과 수요 둔화로 오름세를 이어

   갔음.

   지난 주 국채시장은 지어낸 물가 지표의 예상치 상회와 지어낸 기관의 발표에 금리가 큰 폭으로 상승하고 지어낸 인사들의 매파적

   발언이 이어지며 약세 흐름을 이어갔음.

   크레딧 시장에서는 지표금리가 상승한 가운데 금리 메리트로 수요가 들어와 1년내외 단기물을 중심으로 강세를 보이며 크레딧 스프레드는

   축소되었음.



본보고서는 당사 고객을 위해 배포되는 자료로서 당사의 허가없이 제3자에게 배포하는것을 금합니다.
CONTACT US    대표전화 02. 1234.5678 | 서울시 어딘가
"""
KAP_PAGE2 = "Fixed Income Weekly\n\n  홍길동   대리  (1234-5678) someone@example.invalid\n"


def kap_pages(issue="26-46", month="November 16"):
    return [KAP_PAGE.replace("November 16, Vol.26-46", f"{month}, Vol.{issue}"), KAP_PAGE2]


KIS_GOOD = ("국고 3년물이 한 주 사이 12.5bp 올라 국공채가 약세를 보였다. 지어낸 물가 지표가 예상치를 웃돈 영향이었고, 회사채는 커브가 "
            "평탄해졌으며 CD 91일물 금리는 0.03% 올랐다.")
KAP_GOOD = ("지어낸 물가 지표가 예상보다 높게 나오고 매파적 발언이 겹치며 국채 금리가 크게 올라 약세가 이어졌다. 크레딧 시장은 금리가 오른 데 "
            "따른 수요로 단기물이 강세였고 스프레드가 좁아졌다.")


def kis_main(rows=(("37184", "1212", "20261113", "2026.11.16"), ("37144", "1211", "20261106", "2026.11.09"))):
    """KIS 메인 페이지의 꼴 — Daily 줄과 Weekly 줄(지어낸 글 번호)."""
    daily = '<a href="/post/dawn/37219">\n<dl>\n<dt>KIS(Daily정보)20261120</dt>\n<dd>2026.11.20</dd>\n</dl></a>'
    weekly = "".join(f'<a href="/post/dawn/{p}">\n                        <dl>\n                            <dt>KISWeekly제{i}호({d})</dt>\n'
                     f'                            <dd>{q}</dd>\n                        </dl>\n</a>' for p, i, d, q in rows)
    return ('<div class="report_box"><a href="/post/10088/10253" class="tit">DaIly Report</a>' + daily + '</div>'
            '<div class="report_box"><a href="/post/10106/10254" class="tit">Weekly Report</a>' + weekly + "</div>").encode("utf-8")


def kap_json(rows=(("a" * 32, "261116", "26-46", "2026.11.16", "2026-11-16 16:21"), ("b" * 32, "261109", "26-45", "2026.11.09", "2026-11-09 15:02"))):
    return json.dumps({"totalCnt": 2, "list": [{"rowno": n, "f_nm1": f"{h}_weekly_{ymd}.pdf", "dr_title": f"제 {iss}호 {t}", "dr_dt": at,
                                                "dr_nm": "글쓴이이름", "dr_no": 100 + n}
                                               for n, (h, ymd, iss, t, at) in enumerate(rows)]}, ensure_ascii=False).encode("utf-8")


# ---------- 가짜 수신기 · 쪽 읽기 · claude ----------

class Resp:
    def __init__(self, url, body, status=200, final=None):
        self.url, self.body, self.status, self.final = url, body, status, final or url

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def geturl(self):
        return self.final

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Web:
    """가짜 받는 함수 — pages = {주소: 바이트 | 예외}. 받은 주소와 시간 제한을 적는다."""

    def __init__(self, pages):
        self.pages, self.asked, self.timeouts = dict(pages), [], []

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.asked.append(url)
        self.timeouts.append(timeout)
        got = self.pages.get(url)
        if got is None:
            raise urllib.error.HTTPError(url, 404, "nf", {}, None)
        if isinstance(got, BaseException):
            raise got
        return got if isinstance(got, Resp) else Resp(url, got)


class Clock:
    def __init__(self):
        self.t, self.naps = 0.0, []

    def sleep(self, s):
        self.naps.append(s)
        self.t += s

    def __call__(self):
        return self.t


KIS_PDF = b"%PDF-kis-1212"
KAP_PDF = b"%PDF-kap-26-46"
KAP_URL = "https://www.koreaap.com/cm/files/" + "a" * 32 + "_weekly_261116.pdf"


def site(**over):
    pages = {"https://www.bond.co.kr/": kis_main(), F.KAP_LIST: kap_json(), "https://www.bond.co.kr/post/dawn/37184": KIS_PDF,
             KAP_URL: KAP_PDF}
    pages.update(over)
    return pages


PAGES = {KIS_PDF: kis_pages(), KAP_PDF: kap_pages()}


def pages_of(table=None):
    table = PAGES if table is None else table

    def read(raw):
        if raw not in table:
            raise F.Fetch("pdf")
        return table[raw]
    return read


class Claude:
    """가짜 claude — 점검 호출에는 짧은 답, 본 호출에는 answer(JSON). 부른 명령 · 표준입력을 적는다."""

    def __init__(self, answer=None, code=0, tools=(), tool_use=False):
        self.answer = {"kis": KIS_GOOD, "kap": KAP_GOOD} if answer is None else answer
        self.code, self.tools, self.tool_use, self.calls = code, list(tools), tool_use, []

    def __call__(self, cmd, input=None, cwd=None, env=None, timeout=None, capture_output=None):
        text = input.decode("utf-8")
        self.calls.append(types.SimpleNamespace(cmd=list(cmd), text=text, cwd=cwd, env=dict(env or {}), timeout=timeout,
                                                empty=os.path.isdir(cwd) and not os.listdir(cwd)))
        probe = text == L.PROBE
        asked = set(re.findall(r"^보고서 (\w+) — ", text, flags=re.M))            # 물은 보고서만 답한다(묻지 않은 열쇠가 있으면 답 전체가 버려진다)
        ans = '{"ok":true}' if probe else self.answer if isinstance(self.answer, str) else json.dumps(
            {k: v for k, v in self.answer.items() if k in asked}, ensure_ascii=False)
        init = {"type": "system", "subtype": "init", "tools": self.tools, "mcp_servers": [], "skills": [], "slash_commands": [],
                "model": "claude-fx-1"}
        blocks = [{"type": "text", "text": ans}] + ([{"type": "tool_use", "id": "t", "name": "Bash", "input": {}}] if self.tool_use else [])
        done = {"type": "result", "subtype": "success", "is_error": False, "result": ans,
                "usage": {"input_tokens": 100, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}
        out = "\n".join(json.dumps(e, ensure_ascii=False) for e in (init, {"type": "assistant", "message": {"content": blocks}}, done))
        return types.SimpleNamespace(returncode=self.code, stdout=out.encode("utf-8"), stderr=b"")

    def main_calls(self):
        return [c for c in self.calls if c.text != L.PROBE]


def make_io(web=None, claude=None, table=None, today=TODAY, clock=None):
    clock = clock or Clock()
    return {"run": claude or Claude(), "open": web or Web(site()), "sleep": clock.sleep, "clock": clock, "today": today,
            "pages": pages_of(table), "tool": None, "python": sys.executable}


class FakeExe:
    """claude 실행 파일 자리 — 임시 폴더의 빈 파일(find_claude가 있는 파일인지만 본다)."""

    def __init__(self, case):
        self.dir = tempfile.mkdtemp()
        case.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "claude")
        open(self.path, "w").close()


# ---------- 약속 ----------

class ContractTest(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(F.SCHEMA, "fi-weekly/1")
        self.assertEqual(F.SOURCES, ("kis", "kap"))
        self.assertEqual([k for k, _ in F.ROWS], ["irs_1y", "irs_3y", "crs_1y", "crs_3y", "ss_1y", "ss_3y", "basis_1y", "basis_3y",
                                                    "aa_minus_3y", "a_minus_3y"])
        self.assertEqual(F.KEYS["kis"][:8], F.KEYS["kap"])                          # KAP는 숫자 칸이 없다
        self.assertEqual((F.KIS_HOST, F.KAP_HOST), ("www.bond.co.kr", "www.koreaap.com"))
        self.assertTrue(all(u.startswith("https://") for u in (F.KIS_LIST, F.KIS_PDF, F.KAP_LIST, F.KAP_PDF, F.KAP_BOARD)))
        self.assertEqual((F.DUE_DAYS, F.RETRY_DAYS, F.TRIES, F.SUMMARY_CHARS), (6, 7, 3, 250))
        self.assertEqual(F.COPY_STEMS, K.TH["copy_stems"] + 1)

    def test_command_reuses_the_evening_isolation_with_its_own_system_text(self):
        cmd = F._command("claude", None)
        self.assertEqual(cmd[0], "claude")
        self.assertEqual(cmd[1:], [F.SYSTEM if x == L.SYSTEM else x for x in L.ARGS])
        for flag in ("--safe-mode", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertNotIn(L.SYSTEM, cmd)
        self.assertFalse(re.search(r"[\"'%&]", F.SYSTEM))                             # 명령줄에 실리는 글자 — 셸이 바꾸지 않게
        self.assertEqual(F._command("c", "m-1")[-2:], ["--model", "m-1"])
        self.assertRaises(ValueError, F._command, "c", "bad model")


# ---------- 목록 ----------

class ListTest(unittest.TestCase):
    def test_kis_weekly_rows_only_newest_first(self):
        got = F.kis_list(kis_main().decode("utf-8"))
        self.assertEqual(got, [{"post": 37184, "issue": "1212", "date": "2026-11-13", "posted": "2026-11-16"},
                               {"post": 37144, "issue": "1211", "date": "2026-11-06", "posted": "2026-11-09"}])
        odd = kis_main((("1", "1212", "20261313", "2026.11.16"), ("2", "1213", "20261120", "2026.11.10"), ("3", "1214", "20261120", "2026.11.23")))
        self.assertEqual([x["issue"] for x in F.kis_list(odd.decode())], ["1214"])     # 없는 날짜 · 기준일보다 앞선 게시는 뺀다
        self.assertRaises(F.Bad, F.kis_list, "<html>KIS(Daily정보)</html>")

    def test_kap_rows_use_three_fields_only(self):
        got = F.kap_list(kap_json())
        self.assertEqual([(x["issue"], x["date"], x["posted"]) for x in got], [("26-46", "2026-11-16", "2026-11-16"), ("26-45", "2026-11-09", "2026-11-09")])
        self.assertEqual(set(got[0]), {"name", "issue", "date", "posted", "at"})       # 글쓴이 칸은 읽지 않는다
        self.assertNotIn("글쓴이이름", json.dumps(got, ensure_ascii=False))
        bad = kap_json((("a" * 32, "261117", "26-46", "2026.11.16", "2026-11-16 16:21"), ("x" * 31, "261109", "26-45", "2026.11.09", "2026-11-09 15:02")))
        self.assertRaises(F.Bad, F.kap_list, bad)                                     # 파일 이름의 날짜가 제목과 다르다 · 이름 꼴이 아니다
        for raw in (b"{", b"[]", b'{"list": 3}', b"\xff"):
            self.assertRaises(F.Bad, F.kap_list, raw)


# ---------- 표 ----------

class TableTest(unittest.TestCase):
    def test_numbers_from_the_four_tables(self):
        n = F.kis_numbers(kis_pages(), "2026-11-13")
        self.assertEqual(list(n), list(F.NUM_KEYS))
        self.assertEqual((n["date"], n["prev"], n["credit_date"], n["credit_prev"]), ("2026-11-13", "2026-11-06", "2026-11-13", "2026-11-06"))
        r = n["rows"]
        self.assertEqual(list(r), [k for k, _ in F.ROWS])
        self.assertEqual(r["irs_1y"], [3.1, 10.0])
        self.assertEqual(r["irs_3y"], [3.3025, 15.25])
        self.assertEqual(r["crs_3y"], [3.0, 8.0])
        self.assertEqual(r["ss_1y"], [-2.0, 1.0])                                     # (3.10 − 3.12) · ((0.10 − 0.09))
        self.assertEqual(r["ss_3y"], [1.25, 2.25])
        self.assertEqual(r["basis_3y"], [-30.25, -7.25])
        self.assertEqual(r["aa_minus_3y"], [65.0, -0.7])
        self.assertEqual(r["a_minus_3y"], [175.0, 1.2])

    def test_unicode_minus_and_other_pages_are_fine(self):
        pages = kis_pages(credit=credit_block(minus="−"), extra=["표9. KRW IRS Data 없는 쪽\n자료 : x"])
        self.assertEqual(F.kis_numbers(pages, "2026-11-13")["rows"]["aa_minus_3y"], [65.0, -0.7])

    def bad(self, pages):
        with self.assertRaises(F.Bad) as e:
            F.kis_numbers(pages, "2026-11-13")
        self.assertEqual(e.exception.why, "table")

    def test_every_check_refuses_a_misread_table(self):
        self.bad(kis_pages(date="2026-11-12"))                                        # 표의 이번 주가 보고서 기준일이 아니다
        self.bad(kis_pages(prev="2026-10-30"))                                         # 지난주가 10일보다 앞
        self.bad(kis_pages(irs={k: v for k, v in IRS.items() if k != "3Y"}))          # 3년 칸이 없다
        self.bad(kis_pages(irs={**IRS, "1Y": (25.0, 3.0, 2.5)}))                     # 값이 범위 밖
        pages = kis_pages()
        pages[4] = pages[4].replace("       주간증감     0.1", "       주간증감     0.2", 1)
        self.bad(pages)                                                               # 주간증감 ≠ 이번 주 − 지난주
        pages = kis_pages()
        pages[4] = pages[4].replace("연말대비", "연간대비", 1)
        self.bad(pages)                                                               # 모르는 줄
        self.bad(kis_pages()[:4] + kis_pages()[5:])                                    # KTB 표가 없다(IRS · CRS 쪽이 빠짐)
        pages = kis_pages()
        self.bad(pages + [pages[4]])                                                   # 같은 표가 둘 — 어느 것인지 모른다

    def test_credit_checks(self):
        rows = dict(GRADE_ROWS)
        self.bad(kis_pages(credit=credit_block(this="11/12")))                        # 금주 날짜가 기준일이 아니다
        self.bad(kis_pages(credit=credit_block(prev="10/30")))                        # 전주 날짜가 10일 안에 없다
        self.bad(kis_pages(credit=credit_block(rows={k: rows[k] for k in list(rows)[::-1]})))   # 등급 차례
        self.bad(kis_pages(credit=credit_block(rows={**rows, "A0": [100.0, 99.0] + rows["A0"][2:]})))   # 3년이 등급 따라 줄었다
        self.bad(kis_pages(credit=credit_block(rows={**rows, "AA0": rows["AA0"][:11]})))   # 칸 수
        self.bad(kis_pages(credit=credit_block(rows={**rows, "AA-": rows["AA-"][:5] + [250.0] + rows["AA-"][6:]})))   # 전주 대비 범위 밖
        self.bad(kis_pages(credit=credit_block(rows={k: v for k, v in rows.items() if k != "A+"})))   # 등급이 빠졌다


# ---------- 요약에 읽힐 글 · 표지 ----------

class TextTest(unittest.TestCase):
    def test_kis_text_keeps_six_sections_and_the_market_paragraph(self):
        t = F.kis_text(kis_pages())
        lines = t.split("\n")
        self.assertEqual([x.split(":")[0] for x in lines if not x.startswith("- ")],
                         ["국공채", "금융채", "회사채", "CD/CP", "해외채권", "SWAP", "국공채 시장동향"])
        self.assertIn("해외채권: 지어낸 물가 우려에 미 국채금리 상승", lines)           # 줄바꿈으로 이어진 제목
        self.assertIn("- CD : 감소, CD-은행채 스프레드 감소", lines)
        for gone in ("INDEX", "지수 누적수익률", "가나다라제일차", "ELS", "주가지수", "홍길동", "1234-5678", "KEY POINT", "someone@", "그림1"):
            self.assertNotIn(gone, t)
        self.assertIn("[메일]", t)
        self.assertTrue(lines[-1].startswith("국공채 시장동향: 주 첫 영업일") and "금리가상승했다." in lines[-1])
        self.assertEqual(F.kis_text(kis_pages()[2:]), "")                              # 요약 쪽이 없으면 묻지 않는다

    def test_kap_text_is_the_summary_paragraphs_only(self):
        t = F.kap_text(kap_pages())
        self.assertEqual(t.split("\n")[0], "지어낸 단기 금리는 연말 차환 부담과 수요 둔화로 오름세를 이어갔음.")
        self.assertEqual(len(t.split("\n")), 3)
        for gone in ("수익률곡선", "4.700", "본보고서", "CONTACT", "홍길동", "someone@", "대표전화"):
            self.assertNotIn(gone, t)
        no_caption = kap_pages()[0].replace("▲ 수익률곡선추이와장단기금리등락폭", "")
        t2 = F.kap_text([no_caption])
        self.assertNotIn("4.700", t2)
        self.assertIn("크레딧 스프레드는축소되었음.", t2)
        self.assertEqual(F.kap_text(["Fixed Income Weekly\n본문만"]), "")

    def test_cover_must_match_the_list(self):
        F.check_cover("kis", kis_pages(), {"issue": "1212", "date": "2026-11-13"})
        F.check_cover("kap", kap_pages(), {"issue": "26-46", "date": "2026-11-16"})
        for src, pages, item in (("kis", kis_pages(), {"issue": "1213", "date": "2026-11-13"}),
                                 ("kis", kis_pages(), {"issue": "1212", "date": "2026-11-12"}),
                                 ("kap", kap_pages(), {"issue": "26-45", "date": "2026-11-16"}), ("kap", [], {"issue": "26-46", "date": "2026-11-16"})):
            self.assertRaises(F.Bad, F.check_cover, src, pages, item)


# ---------- 요약 검사 ----------

class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.kis, self.kap = F.kis_text(kis_pages()), F.kap_text(kap_pages())

    def test_own_words_pass(self):
        self.assertIsNone(F.summary_code("kis", KIS_GOOD, self.kis))
        self.assertIsNone(F.summary_code("kap", KAP_GOOD, self.kap))

    def test_each_check(self):
        cases = [("kis", None, "none"), ("kis", "짧다.", "shape"), ("kis", KIS_GOOD + " 셋째 문장이다. 넷째 문장이다.", "shape"),
                 ("kis", KIS_GOOD.replace("올랐다.", "올랐다"), "shape"), ("kis", "가" * 120 + "다. " + "나" * 140 + "다.", "shape"),
                 ("kis", KIS_GOOD.replace("국공채가", "국공채가 \"크게\""), "shape"), ("kis", KIS_GOOD + " www.example.com 이다.", "shape"),
                 ("kis", "국고 3년물이 12.5bp 올랐다. 앞으로 금리는 더 오를 것으로 보인다.", "banned"),
                 ("kis", "국고 3년물이 12.5bp 올라 국공채가 약세였다. 은행채는 매수 우위였다.", "banned"),
                 ("kis", "주 첫 영업일 국내 채권시장은 지어낸 증시 호조에 약세로 출발했고 금리가 올랐다.", "copy"),
                 ("kis", "국고 3년물이 한 주 사이 13.5bp 올라 국공채가 약세를 보였다. 회사채는 커브가 평탄해졌다.", "number"),
                 ("kis", "국고 3년물이 한 주 사이 12.5bp 올라 국공채가 약세를 보였다. 기준금리는 동결됐다.", "term"),
                 ("kis", "국고 3년물이 한 주 사이 12.5bp 올라 국공채가 약세를 보였다. QQZ 쪽 영향이 컸다.", "name"),
                 ("kap", "국채 금리가 크게 올랐다. CD 91일물은 3.37%로 마감했다는 사실이 적혔다.", "number"),
                 ("kap", "지어낸 물가 지표 상회로 국채 금리가 크게 올랐다. 단기물은 1년 안팎이 강세였다.", "digits")]
        for src, s, want in cases:
            with self.subTest(s=s):
                self.assertEqual(F.summary_code(src, s, self.kis if src == "kis" else self.kap), want)

    def test_copy_rule_is_the_evening_one_with_six_stems(self):
        text = "가나 다라 마바 사아 자차 카타 파하 거너 더러"
        five = "가나 다라 마바 사아 자차 이야기는 다른 데로 흘렀다."
        six = "가나 다라 마바 사아 자차 카타 이야기는 다른 데로 흘렀다."
        self.assertFalse(K.ok_copy(five, [text]))                                    # 저녁판은 다섯 어절에서 걸린다
        self.assertTrue(F.ok_copy(five, [text]))
        self.assertFalse(F.ok_copy(six, [text]))


# ---------- 파일의 꼴 ----------

class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.exe = FakeExe(self).path
        self.doc, _ = F.update(None, set(), TODAY, make_io(), {}, claude=self.exe)

    def test_a_good_file(self):
        F.validate(self.doc, TODAY)
        self.assertEqual([r["src"] for r in self.doc["reports"]], ["kis", "kap"])
        self.assertEqual(json.loads(F.dump(self.doc)), self.doc)
        self.assertLess(len(F.dump(self.doc)), F.MAX_BYTES)

    def broken(self, change):
        d = json.loads(F.dump(self.doc))
        change(d)
        with self.assertRaises(F.Bad):
            F.validate(d, TODAY)

    def test_mutations_fail(self):
        kis, kap = 0, 1
        self.broken(lambda d: d.update(schema="fi-weekly/2"))
        self.broken(lambda d: d.update(asof="2026-11-19"))                             # 내일모레
        self.broken(lambda d: d["reports"].reverse())
        self.broken(lambda d: d["reports"].append(d["reports"][0]))
        self.broken(lambda d: d["reports"][kis].update(url="https://www.bond.co.kr/post/dawn/1?x=1"))
        self.broken(lambda d: d["reports"][kis].update(url="https://evil.example/post/dawn/1"))
        self.broken(lambda d: d["reports"][kap].update(url=KAP_URL))                    # KAP는 파일이 아니라 게시판으로
        self.broken(lambda d: d["reports"][kis].update(issue="12a"))
        self.broken(lambda d: d["reports"][kap].update(posted="2026-11-15"))           # 게시가 기준일보다 앞
        self.broken(lambda d: d["reports"][kis].update(summary="앞으로 금리는 오를 것으로 보인다는 말이 적혔다."))
        self.broken(lambda d: d["reports"][kap].update(summary="국채 금리가 3bp 올랐고 크레딧은 강세를 이어갔다."))
        self.broken(lambda d: d["reports"][kis].update(summary=None))                   # 사유 없는 빈 요약
        self.broken(lambda d: d["reports"][kis].update(summary=None, summary_note="model"))   # 모델 이름이 남았다
        self.broken(lambda d: d["reports"][kis].update(summary_note="model"))
        self.broken(lambda d: d["reports"][kis].update(numbers=None))
        self.broken(lambda d: d["reports"][kis].update(numbers_note="table"))
        self.broken(lambda d: d["reports"][kis]["numbers"]["rows"].update(irs_1y=[25.0, 1.0]))
        self.broken(lambda d: d["reports"][kis]["numbers"]["rows"].update(ss_1y=[1.0, 999.0]))
        self.broken(lambda d: d["reports"][kis]["numbers"]["rows"].pop("a_minus_3y"))
        self.broken(lambda d: d["reports"][kis]["numbers"].update(prev="2026-11-13"))
        self.broken(lambda d: d["reports"][kap].update(numbers=None, numbers_note="table"))
        self.broken(lambda d: d["reports"][kis].update(model="bad model"))

    def test_empty_reports_and_summary_less_entries_are_fine(self):
        F.validate(F.empty(TODAY), TODAY)
        d = json.loads(F.dump(self.doc))
        d["reports"][0].update(summary=None, summary_note="copy", model=None, numbers=None, numbers_note="table")
        F.validate(d, TODAY)


# ---------- 받기 ----------

class NetTest(unittest.TestCase):
    def test_hosts_scheme_and_shape(self):
        n = F.Net(Web({}), *(lambda c: (c.sleep, c))(Clock()))
        for url in ("http://www.bond.co.kr/", "https://bond.co.kr/", "https://www.bond.co.kr:8443/", "https://u:p@www.bond.co.kr/",
                    "https://evil.example/", "https://www.koreaap.com.evil.example/"):
            with self.assertRaises(F.Fetch) as e:
                n.get(url, 100)
            self.assertEqual(e.exception.code, "format")
        self.assertEqual(n.used, 0)

    def test_redirects_errors_size_and_spacing(self):
        clock = Clock()
        web = Web({"https://www.bond.co.kr/a": b"x" * 10,
                   "https://www.bond.co.kr/r": urllib.error.HTTPError("u", 302, "moved", {"Location": "https://evil.example/"}, None),
                   "https://www.bond.co.kr/t": urllib.error.URLError(TimeoutError()),
                   "https://www.bond.co.kr/o": Resp("u", b"x", final="https://evil.example/x"),
                   "https://www.bond.co.kr/s": Resp("u", b"x", status=204)})
        n = F.Net(web, clock.sleep, clock)
        self.assertEqual(n.get("https://www.bond.co.kr/a", 10), b"x" * 10)
        for url, code in (("https://www.bond.co.kr/a", "format"), ("https://www.bond.co.kr/r", "fetch"), ("https://www.bond.co.kr/t", "timeout"),
                          ("https://www.bond.co.kr/o", "fetch"), ("https://www.bond.co.kr/s", "fetch"), ("https://www.bond.co.kr/none", "fetch")):
            with self.assertRaises(F.Fetch) as e:
                n.get(url, 9)
            self.assertEqual(e.exception.code, code, url)
        self.assertEqual(clock.naps, [F.GAP_S] * 6)                                    # 요청 사이 GAP_S초
        self.assertTrue(all(t <= F.REQ_S for t in web.timeouts))

    def test_budget(self):
        clock = Clock()
        n = F.Net(Web({"https://www.bond.co.kr/a": b"x"}), clock.sleep, clock, budget=10)
        clock.t = 9.5
        with self.assertRaises(F.Fetch) as e:
            n.get("https://www.bond.co.kr/a", 9)
        self.assertEqual(e.exception.code, "budget")
        clock.t = 3
        web = Web({"https://www.bond.co.kr/a": b"x"})
        n = F.Net(web, clock.sleep, clock, budget=10)
        n.get("https://www.bond.co.kr/a", 9)
        self.assertEqual(web.timeouts, [10.0])                                         # min(REQ_S, 남은 예산)

    def test_pdf_pages_refuses_non_pdf(self):
        with self.assertRaises(F.Fetch) as e:
            F.pdf_pages(b"<html>")
        self.assertEqual(e.exception.code, "pdf")


# ---------- 한 번 돌기 ----------

class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.exe = FakeExe(self).path

    def run_update(self, old=None, off=(), today=TODAY, state=None, web=None, claude=None, table=None, force=False):
        self.web, self.claude = web or Web(site()), claude or Claude()
        self.state = {} if state is None else state
        io_ = make_io(self.web, self.claude, table, today)
        return F.update(old, set(off), today, io_, self.state, force=force, claude=self.exe)

    def test_first_run_fetches_both_and_asks_once(self):
        doc, seen = self.run_update()
        F.validate(doc, TODAY)
        kis, kap = doc["reports"]
        self.assertEqual((kis["issue"], kis["date"], kis["posted"], kis["url"]), ("1212", "2026-11-13", "2026-11-16", "https://www.bond.co.kr/post/dawn/37184"))
        self.assertEqual((kap["issue"], kap["date"], kap["url"]), ("26-46", "2026-11-16", F.KAP_BOARD))
        self.assertEqual((kis["summary"], kap["summary"], kis["model"]), (KIS_GOOD, KAP_GOOD, "claude-fx-1"))
        self.assertEqual(kis["numbers"]["rows"]["irs_1y"], [3.1, 10.0])
        self.assertEqual(seen, {"kis": "new", "num": "ok", "kap": "new", "requests": 4, "sum": "ok"})
        self.assertEqual(self.web.asked, ["https://www.bond.co.kr/", "https://www.bond.co.kr/post/dawn/37184", F.KAP_LIST, KAP_URL])
        self.assertEqual(len(self.claude.calls), 2)                                    # 점검 한 번 + 본 호출 한 번
        main = self.claude.main_calls()[0]
        self.assertTrue(main.empty)
        self.assertIn("보고서 kis — 숫자 씀", main.text)
        self.assertIn("보고서 kap — 숫자 없음", main.text)
        marks = re.findall(r"<<<자료 ([0-9a-f]{16}) (시작|끝)>>>", main.text)
        self.assertEqual([m[1] for m in marks], ["시작", "끝"])
        body = main.text.split(f"<<<자료 {marks[0][0]} 시작>>>\n")[1].split(f"\n<<<자료 {marks[0][0]} 끝>>>")[0]
        self.assertTrue(all(x.startswith(("| ", "보고서 ")) for x in body.split("\n")))
        for gone in ("홍길동", "1234-5678", "someone@", "글쓴이이름", "가나다라제일차"):
            self.assertNotIn(gone, main.text)
        self.assertEqual(self.state, {"kis": {"issue": "1212", "tries": 0}, "kap": {"issue": "26-46", "tries": 0}})

    def test_the_next_days_wait_and_the_next_week_fetches(self):
        doc, _ = self.run_update()
        for days in range(1, F.DUE_DAYS):                                              # KAP 게시(11-16) 뒤 닷새 — 기다린다
            _, seen = self.run_update(doc, today=datetime.date(2026, 11, 16) + datetime.timedelta(days=days))
            self.assertEqual((seen["kis"], seen["kap"], seen["requests"]), ("wait", "wait", 0))
            self.assertEqual(self.web.asked, [])
        same, seen = self.run_update(doc, today=datetime.date(2026, 11, 23))           # 엿새째: 목록만 본다(새 호 없음)
        self.assertEqual((seen["kis"], seen["kap"], seen["requests"]), ("same", "same", 2))
        self.assertEqual(same["reports"], doc["reports"])
        self.assertEqual(self.claude.calls, [])
        web = Web(site(**{"https://www.bond.co.kr/": kis_main((("37300", "1213", "20261120", "2026.11.23"),)),
                          "https://www.bond.co.kr/post/dawn/37300": b"%PDF-kis-1213"}))
        table = {**PAGES, b"%PDF-kis-1213": kis_pages("1213", "2026-11-20", "2026-11-13")}
        new, seen = self.run_update(doc, today=datetime.date(2026, 11, 23), web=web, table=table)
        self.assertEqual((seen["kis"], seen["kap"]), ("new", "same"))
        self.assertEqual((new["reports"][0]["issue"], new["reports"][0]["numbers"]["prev"]), ("1213", "2026-11-13"))
        self.assertEqual(new["reports"][1], doc["reports"][1])
        self.assertNotIn("보고서 kap", self.claude.main_calls()[0].text)                # 새 호만 묻는다

    def test_off_sources_are_removed_and_never_fetched(self):
        doc, _ = self.run_update()
        got, seen = self.run_update(doc, off={"kis"})
        self.assertEqual([r["src"] for r in got["reports"]], ["kap"])
        self.assertEqual(seen["kis"], "off")
        self.assertNotIn("https://www.bond.co.kr/", self.web.asked)
        got, seen = self.run_update(doc, off={"kis", "kap"})
        self.assertEqual((got["reports"], seen["requests"]), ([], 0))
        self.assertEqual(F.parse_off("kis, KAP"), {"kis", "kap"})
        self.assertEqual(F.parse_off(""), set())
        self.assertEqual(F.parse_off("all"), {"kis", "kap"})
        self.assertEqual(F.parse_off("kis,typo"), {"kis", "kap"})                     # 모르는 낱말 — 닫는 쪽으로

    def test_failures_keep_what_is_up(self):
        doc, _ = self.run_update()
        later = datetime.date(2026, 11, 23)
        for over, code in ((({"https://www.bond.co.kr/": urllib.error.URLError("x")}), "fetch"),
                           (({"https://www.bond.co.kr/": b"<html>no rows</html>"}), "format"),
                           (({"https://www.bond.co.kr/": kis_main((("37300", "1213", "20261120", "2026.11.23"),))}), "fetch")):   # PDF 404
            with self.subTest(code=code):
                got, seen = self.run_update(doc, today=later, web=Web(site(**over)))
                self.assertEqual(seen["kis"], code)
                self.assertEqual(got["reports"][0], doc["reports"][0])
        web = Web(site(**{"https://www.bond.co.kr/": kis_main((("37300", "1213", "20261120", "2026.11.23"),)),
                          "https://www.bond.co.kr/post/dawn/37300": KIS_PDF}))       # 표지는 1212호
        got, seen = self.run_update(doc, today=later, web=web)
        self.assertEqual(seen["kis"], "cover")
        self.assertEqual(got["reports"][0], doc["reports"][0])

    def test_a_misread_table_drops_the_numbers_only(self):
        pages = kis_pages()
        pages[4] = pages[4].replace("주간증감", "주간 증감")
        doc, seen = self.run_update(table={**PAGES, KIS_PDF: pages})
        kis = doc["reports"][0]
        self.assertEqual((kis["numbers"], kis["numbers_note"], kis["summary"], seen["num"]), (None, "table", KIS_GOOD, "table"))
        F.validate(doc, TODAY)

    def test_model_failure_keeps_the_entry_without_summary_and_retries(self):
        doc, seen = self.run_update(claude=Claude(code=1))
        self.assertEqual([(r["summary"], r["summary_note"], r["model"]) for r in doc["reports"]], [(None, "model", None)] * 2)
        self.assertEqual((seen["sum"], seen["ask"]), ("model", "exit"))
        self.assertEqual(self.state, {})                                               # 모델 실패는 셈하지 않는다
        F.validate(doc, TODAY)
        again, seen = self.run_update(doc, today=datetime.date(2026, 11, 18))           # 게시 뒤 7일 안 — 다시 받고 다시 묻는다
        self.assertEqual((seen["kis"], seen["kap"], seen["sum"]), ("retry", "retry", "ok"))
        self.assertEqual(again["reports"][0]["summary"], KIS_GOOD)
        _, seen = self.run_update(doc, today=datetime.date(2026, 11, 23))               # 7일이 지나면 다시 묻지 않는다(새 호를 기다린다)
        self.assertEqual((seen["kis"], seen["kap"]), ("same", "same"))
        for claude, code in ((Claude(tools=["Bash"]), "tools"), (Claude(tool_use=True), "tool_use"), (Claude(answer="not json"), "json")):
            _, seen = self.run_update(claude=claude)
            self.assertEqual((seen["sum"], seen["ask"]), ("model", code))

    def test_checked_out_answers_count_up_to_three_tries(self):
        bad = Claude(answer={"kis": "주 첫 영업일 국내 채권시장은 지어낸 증시 호조에 약세로 출발했고 금리가 올랐다.", "kap": KAP_GOOD})
        doc, seen = self.run_update(claude=bad)
        self.assertEqual((doc["reports"][0]["summary_note"], seen["sum"]), ("copy", "copy_ok"))
        self.assertEqual(self.state["kis"], {"issue": "1212", "tries": 1})
        state = self.state
        for n in (2, 3):
            doc, seen = self.run_update(doc, state=state, claude=bad, today=datetime.date(2026, 11, 18))
            self.assertEqual((seen["kis"], seen["kap"], state["kis"]["tries"]), ("retry", "wait", n))
        _, seen = self.run_update(doc, state=state, claude=bad, today=datetime.date(2026, 11, 18))
        self.assertEqual((seen["kis"], seen["requests"]), ("wait", 0))                 # 세 번 걸렸으면 새 호까지 기다린다

    def test_force_and_short_text(self):
        doc, _ = self.run_update()
        _, seen = self.run_update(doc, today=datetime.date(2026, 11, 18), force=True)
        self.assertEqual((seen["kis"], seen["kap"]), ("retry", "retry"))
        table = {**PAGES, KAP_PDF: [kap_pages()[0].split("▲")[0] + "▲ 그림\n짧은 글만 있다.\n본보고서는 x"]}
        doc, seen = self.run_update(table=table)
        self.assertEqual((doc["reports"][1]["summary_note"], seen["sum"]), ("text", "ok"))   # 묻지 않았다
        self.assertNotIn("보고서 kap", self.claude.main_calls()[0].text)


# ---------- 게시(가짜 git) ----------

def name_of(cmd):
    if cmd[0] != "git":
        if cmd[0] == "gh":
            return "gh"
        return "blind" if cmd[-1].replace("\\", "/").endswith("scripts/check_blind.py") else "other"
    rest = list(cmd[1:])
    while rest and rest[0] == "-c":
        rest = rest[2:]
    return rest[0]


class Tool:
    def __init__(self, **answers):
        self.calls = []
        self.answers = {k.replace("_", "-"): v for k, v in answers.items()}

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
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


def good_tool(**more):
    return Tool(**{"status": (0, NEW), "rev_parse": lambda cmd: (0, "aaa\naaa\n" if "HEAD" in cmd else "aaa\n"), "rev_list": (0, "1\n"),
                   "diff": (0, PATH + "\n"), "gh": (0, json.dumps([{"name": "EVENING_ENABLED", "value": "true"}])), **more})


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.doc, _ = F.update(None, set(), TODAY, make_io(), {}, claude=FakeExe(self).path)

    def test_pushes_one_file(self):
        t = good_tool()
        self.assertEqual(F.publish(self.repo, self.doc, TODAY, t), "pushed")
        self.assertEqual(t.names(), ["status", "blind", "rev-parse", "add", "commit", "rev-list", "diff", "push"])
        with open(os.path.join(self.repo, *PATH.split("/")), "rb") as f:
            self.assertEqual(f.read(), F.dump(self.doc))
        commit = next(c for c in t.calls if name_of(c) == "commit")
        self.assertIn("data: 2026-11-17 평가사 주간 보고서", commit)
        self.assertEqual(commit[-2:], ["--", PATH])
        push = next(c for c in t.calls if name_of(c) == "push")
        self.assertEqual(push[:5], ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"])

    def test_same_reports_do_not_commit(self):
        F._write(self.repo, F.dump(self.doc))
        t = good_tool()
        later = json.loads(F.dump(self.doc))
        later["asof"] = "2026-11-18"
        self.assertEqual(F.publish(self.repo, later, datetime.date(2026, 11, 18), t), "same")   # 날짜만 다르다
        self.assertEqual(t.names(), [])

    def test_nothing_to_carry_on_the_first_run_writes_nothing(self):
        t = good_tool()
        self.assertEqual(F.publish(self.repo, F.empty(TODAY), TODAY, t), "same")
        self.assertEqual(t.names(), [])
        F._write(self.repo, F.dump(self.doc))                                         # 올라 있던 것을 모두 내리는 실행은 빈 파일을 올린다
        t = good_tool(status=(0, MOD))
        self.assertEqual(F.publish(self.repo, F.empty(TODAY), TODAY, t), "pushed")

    def test_stops(self):
        for tool, code in ((good_tool(status=(0, NEW + " M site/x.js\n")), "scope"), (good_tool(blind=1), "blind"),
                           (good_tool(rev_parse=(0, "aaa\nbbb\n")), "head"), (good_tool(rev_list=(0, "2\n")), "commits"),
                           (good_tool(push=1, rev_parse=lambda c: (0, "aaa\naaa\n" if "HEAD" in c else "aaa\n")), "push")):
            with self.subTest(code=code):
                if os.path.exists(os.path.join(self.repo, *PATH.split("/"))):
                    os.remove(os.path.join(self.repo, *PATH.split("/")))
                with self.assertRaises(F.Stop) as e:
                    F.publish(self.repo, self.doc, TODAY, tool)
                self.assertEqual(e.exception.code, code)

    def test_push_refused_and_main_moved_retries_once(self):
        heads = iter(["aaa\naaa\n", "bbb\n"])
        file = os.path.join(self.repo, *PATH.split("/"))
        t = good_tool(push=[1, 0], rev_parse=lambda c: (0, next(heads)),
                      checkout=lambda c: (os.remove(file), 0)[1])                     # 새 main의 끝으로 — 올리지 못한 파일은 사라진다
        self.assertEqual(F.publish(self.repo, self.doc, TODAY, t), "pushed")
        self.assertEqual(t.names().count("push"), 2)
        self.assertEqual(t.names().count("checkout"), 1)

    def test_switch(self):
        self.assertEqual(F.switch(self.repo, good_tool()), set())
        t = good_tool(gh=(0, json.dumps([{"name": "FI_WEEKLY_OFF", "value": "kap"}])))
        self.assertEqual(F.switch(self.repo, t), {"kap"})
        for bad in ((1, ""), (0, "not json"), (0, "{}"), (0, "[1]")):
            with self.assertRaises(F.Stop) as e:
                F.switch(self.repo, good_tool(gh=bad))
            self.assertEqual(e.exception.code, "switch")


# ---------- 한 번에 돌리기 ----------

class MainTest(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.log = os.path.join(self.repo, "..", os.path.basename(self.repo) + ".log")
        self.addCleanup(lambda: os.path.exists(self.log) and os.remove(self.log))
        self.exe = FakeExe(self).path

    def tool(self, **more):
        file = os.path.join(self.repo, *PATH.split("/"))
        return good_tool(status=lambda c: (0, NEW if os.path.exists(file) else ""), **more)

    def main(self, extra=(), tool=None, claude=None, web=None):
        out = io.StringIO()
        clock = Clock()
        with redirect_stdout(out):
            code = F.main(["--repo-dir", self.repo, "--log", self.log, "--claude", self.exe, *extra], run=claude or Claude(),
                tool=tool or self.tool(),
                open_=web or Web(site()), sleep=clock.sleep, clock=clock, now=lambda: datetime.datetime(2026, 11, 17, 17, 45, tzinfo=KST),
                pages=pages_of())
        return code, out.getvalue()

    def test_dry_run_writes_under_work_and_logs_codes_only(self):
        code, out = self.main(["--dry-run"])
        self.assertEqual(code, 0)
        with open(F.dry_out(self.repo), "rb") as f:
            doc = F.validate(json.loads(f.read().decode("utf-8")), TODAY)
        self.assertEqual(len(doc["reports"]), 2)
        line = open(self.log, encoding="utf-8").read().strip()
        self.assertRegex(line, r"^2026-11-17T17:45:00\+09:00 \[fi_weekly\] run code=ok result=dry ")
        for word in ("지어낸", "국공채", "3.1", "1212"):
            self.assertNotIn(word, line)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "data")))           # 마른 실행은 data/에 쓰지 않는다

    def test_publish_run_and_stop_codes(self):
        tool = self.tool()
        code, out = self.main(tool=tool)
        self.assertEqual(code, 0)
        self.assertIn("result=pushed", out)
        self.assertEqual(tool.names()[:2], ["gh", "status"])                          # 스위치 → sync
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".work", "fi_weekly", "state.json")))
        code, out = self.main(tool=self.tool(gh=(1, "")))
        self.assertEqual(code, 2)
        self.assertIn("code=switch", out)
        tool = self.tool(blind=1)
        code, out = self.main(tool=tool)
        self.assertEqual(code, 2)
        self.assertIn("code=blind", out)
        self.assertIn(["git", "reset", "--quiet", "--", PATH], tool.calls)            # 멈추면 정리한다(tidy)
        self.assertFalse(os.path.exists(os.path.join(self.repo, *PATH.split("/"))))

    def test_unexpected_error_logs_the_kind_only(self):
        def boom(raw):
            raise RuntimeError("비밀 " + CANARY)
        out = io.StringIO()
        with redirect_stdout(out):
            code = F.main(["--repo-dir", self.repo, "--log", self.log, "--dry-run"], open_=Web(site()), sleep=lambda s: None,
                          now=lambda: datetime.datetime(2026, 11, 17, 17, 45, tzinfo=KST), pages=boom)
        self.assertEqual(code, 1)
        self.assertIn("code=error kind=RuntimeError", out.getvalue())
        self.assertNotIn(CANARY, out.getvalue() + open(self.log, encoding="utf-8").read())

    def test_bad_model_name_is_refused_early(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            F.parse(["--repo-dir", self.repo, "--model", "a b"])


# ---------- 진짜 git ----------

@unittest.skipUnless(shutil.which("git"), "git이 없다")
class RealGitTest(unittest.TestCase):
    """임시 폴더의 진짜 git — 원격은 그 안의 bare 저장소. 공개 전 검사 · gh만 가짜."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.origin, self.pc, self.other = (os.path.join(self.tmp, n) for n in ("origin.git", "pc", "other"))
        self.git(self.tmp, "init", "--quiet", "--bare", "--initial-branch=main", self.origin)
        for repo in (self.pc, self.other):
            self.git(self.tmp, "clone", "--quiet", self.origin, repo)
            for k, v in (("user.name", "fx"), ("user.email", "fx@example.invalid"), ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
                self.git(repo, "config", k, v)
        os.makedirs(os.path.join(self.other, "data"))
        for name, body in (("data/digest_picks.json", "{}"), ("data/people_remarks.json", "{}"), (".gitignore", ".work/\n")):
            with open(os.path.join(self.other, *name.split("/")), "w", encoding="utf-8") as f:
                f.write(body)
        self.git(self.other, "add", "-A")
        self.git(self.other, "commit", "--quiet", "-m", "seed")
        self.git(self.other, "push", "--quiet", "origin", "HEAD:main")
        self.git(self.pc, "fetch", "--quiet", "origin", "main")
        self.git(self.pc, "checkout", "--quiet", "--detach", "origin/main")
        self.blind, self.exe = 0, FakeExe(self).path

    def git(self, cwd, *args):
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=120)
        self.assertEqual(r.returncode, 0, (args[:2], r.stderr[-300:]))
        return r.stdout.decode("utf-8", "replace")

    def tool(self, cmd, **kw):
        if cmd[0] == "gh":
            return subprocess.CompletedProcess(cmd, 0, b"[]", b"")
        if cmd[0] != "git":
            return subprocess.CompletedProcess(cmd, self.blind, b"", b"")
        return subprocess.run(cmd, **kw)

    def run_main(self, day=datetime.datetime(2026, 11, 17, 17, 45, tzinfo=KST), web=None):
        clock = Clock()
        with redirect_stdout(io.StringIO()):
            return F.main(["--repo-dir", self.pc, "--log", os.path.join(self.tmp, "fi.log"), "--claude", self.exe], run=Claude(),
                          tool=self.tool, open_=web or Web(site()), sleep=clock.sleep, clock=clock, now=lambda: day, pages=pages_of())

    def status(self):
        return self.git(self.pc, "status", "--porcelain", "--untracked-files=all")

    def test_first_upload_then_wait_then_leftovers_are_cleaned(self):
        self.assertEqual(self.run_main(), 0)
        self.git(self.other, "fetch", "--quiet", "origin", "main")
        raw = self.git(self.other, "show", f"origin/main:{PATH}").encode("utf-8")
        F.validate(json.loads(raw.decode("utf-8")), TODAY)
        self.assertEqual(self.git(self.other, "log", "-1", "--format=%s", "origin/main").strip(), "data: 2026-11-17 평가사 주간 보고서")
        self.assertEqual(self.git(self.other, "diff", "--name-only", "origin/main~1", "origin/main").strip(), PATH)
        count = self.git(self.other, "rev-list", "--count", "origin/main").strip()
        self.assertEqual(self.run_main(datetime.datetime(2026, 11, 18, 17, 45, tzinfo=KST)), 0)   # 때가 아님 — 커밋 없음
        self.assertEqual(self.git(self.other, "rev-list", "--count", "origin/main").strip(), count)
        for name in (PATH, "data/people_remarks.json", "data/digest_picks.json"):     # 세 게시기가 끊겨 남긴 것
            with open(os.path.join(self.pc, *name.split("/")), "w", encoding="utf-8") as f:
                f.write('{"left":1}')
        self.git(self.pc, "add", "--", "data/people_remarks.json")
        F.sync(self.pc, self.tool)
        self.assertEqual(self.status(), "")
        with open(os.path.join(self.pc, "site.js"), "w") as f:
            f.write("x")
        with self.assertRaises(F.Stop) as e:
            F.sync(self.pc, self.tool)
        self.assertEqual(e.exception.code, "dirty")

    def test_failure_leaves_the_folder_ready_for_the_other_publishers(self):
        self.blind = 1
        self.assertEqual(self.run_main(), 2)
        self.assertEqual(self.status(), "")
        self.assertFalse(os.path.exists(os.path.join(self.pc, *PATH.split("/"))))
        F._picks().sync(self.pc, self.tool)                                            # 저녁판 게시는 막히지 않는다


# ---------- 올라 있는 파일 · 화면 · 문서 ----------

@unittest.skipUnless(os.path.exists(DATA_FILE), "data/fi_weekly.json이 아직 없다")
class DataFileTest(unittest.TestCase):
    """올라 있는 공개 파일을 게시기와 같은 검사로 — 손으로 고쳐 깨뜨린 파일이 배포되지 않게(CI의 check가 배포 앞에서 돈다)."""

    def test_published_file_follows_the_contract(self):
        with open(DATA_FILE, "rb") as f:
            raw = f.read()
        doc = F.validate(json.loads(raw.decode("utf-8")), datetime.date.today())
        self.assertEqual(F.dump(doc), raw)


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
        return f.read()


class SiteTest(unittest.TestCase):
    def test_page_wiring(self):
        page = read("site", "index.html")
        for snippet in ('getJson("data/fi_weekly.json")', '<script src="fiweekly.js"></script>', "window.FiWeekly.render(",
                        '<a href="data/fi_weekly.json">', '<section id="fiweekly-wrap" hidden', '<div id="fiweekly-body"></div>',
                        'document.getElementById("fiweekly-wrap").hidden = !(available.fiweekly && (activeView === "korea" || activeView.startsWith("korea-")));',
                        "fiweekly: false }", "<h3>평가사 주간 보고서</h3>"):
            self.assertIn(snippet, page)
        self.assertLess(page.index('<section id="korea-market"'), page.index('<section id="fiweekly-wrap"'))

    def test_screen_script_matches_the_module_and_writes_text_only(self):
        js = read("site", "fiweekly.js")
        pick = lambda name: js[js.index(f"const {name} = "):].split(";\n", 1)[0]
        self.assertEqual(re.findall(r'"(\w+)"', pick("SOURCES")), list(F.SOURCES))
        self.assertEqual([tuple(x) for x in re.findall(r'\["(\w+)", "(%|bp)"\]', pick("ROWS"))], list(F.ROWS))
        self.assertEqual(re.findall(r"(\w+): \"", pick("NOTES")), list(F.NOTES))
        self.assertEqual(re.findall(r"(\w+): \"", pick("NUM_NOTES")), list(F.NUM_NOTES))
        self.assertIn(f'const KAP_BOARD = "{F.KAP_BOARD}";', js)
        self.assertIn(r"const KIS_ITEM = /^https:\/\/www\.bond\.co\.kr\/post\/dawn\/[0-9]{1,9}$/;", js)
        self.assertIn('doc.schema !== "' + F.SCHEMA + '"', js)
        self.assertIn(f"r.summary.length <= {F.SUMMARY_CHARS}", js)
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval(", "<img", "src="):
            self.assertNotIn(tok, js)

    def test_workflow_runs_the_node_test(self):
        wf = read(".github", "workflows", "daily.yml")
        self.assertIn("node --test scripts/test_fiweekly_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_evening_task_runs_this_step_first(self):
        ps = read("scripts", "evening", "Evening-Summary.ps1")
        body = ps[ps.index("#>"):]
        fi, people = body.index('$fi = Join-Path $repo "scripts\\fi_weekly.py"'), body.index('$people = Join-Path $repo "scripts\\people_push.py"')
        evening = body.index('$script = Join-Path $repo "scripts\\evening\\evening_llm.py"')
        self.assertLess(fi, people)
        self.assertLess(people, evening)
        step = body[body.index("# Valuation-house weekly reports"):body.index("# Fed people remarks")]
        code = "\n".join(x for x in step.split("\n") if not x.lstrip().startswith("#"))
        self.assertIn('"--repo-dir"', code)
        self.assertNotIn("$code", code)                                               # 저녁판의 종료코드 · 오류 파일을 건드리지 않는다
        self.assertNotIn("$ErrorFile", code)
        self.assertTrue(ps.isascii())

    def test_only_the_guarded_test_imports_the_module(self):
        users = set()
        for d in (HERE, os.path.join(HERE, "evening")):
            for name in os.listdir(d):
                if name.endswith(".py") and name != "fi_weekly.py":
                    with open(os.path.join(d, name), encoding="utf-8") as f:
                        if re.search(r"^\s*(import|from)\s+fi_weekly\b", f.read(), flags=re.M):
                            users.add(name)
        self.assertEqual(users, {"test_fi_weekly.py"})
        self.assertFalse(re.search(r"^\s*(import|from)\s+people_push\b", read("scripts", "fi_weekly.py"), flags=re.M))


class ReadmeTest(unittest.TestCase):
    def test_readme_counts_and_section(self):
        readme = read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertRegex(py_part, rf"(^| · )평가사 주간 보고서 {mine}( · |$)")
        cjs = len(re.findall(r"^test\(", read("scripts", "test_fiweekly_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^| · )평가사 주간 보고서 그리기 {cjs}( · |\)|$)")
        sec = readme[readme.index("### 평가사 주간 보고서"):]
        sec = sec[:sec.index("\n## ")]
        for word in ("fi_weekly.py", "data/fi_weekly.json", "FI_WEEKLY_OFF", "Evening-Summary.ps1", "fi-weekly.log", "pypdf",
                     "bond.co.kr", "koreaap.com", "평가사 산출값", "요청이 있으면", "계약"):
            self.assertIn(word, sec, word)


if __name__ == "__main__":
    unittest.main()
