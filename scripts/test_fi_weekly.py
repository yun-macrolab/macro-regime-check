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
CORP = """회사채 : 지어낸 회사채 금리 상승

평가담당자                    KEY POINT

김아무 대리     02) 1234-5679 •  회사채 커브 플래트닝

  I.  회사채 시장동향

    회사채 3년 AA- 등급 스프레드는 전 주 대비 0.7bp 축소된 65.0bp를 기록하였다. 금주 회사채 금리는 지어낸 물가 우려에 전 구간

상승했고, 회사채 스프레드는 단기를 중심으로 강세를 나타냈다.

그림1. 회사채 금리추이                  (단위 : 억 원)

"""
SWAP_HEAD = """SWAP : CD 91일물 금리 0.03% 상승

평가담당자                    KEY POINT

이아무 과장     02) 1234-5670 •  IRS 금리 상승세, CRS 금리 상승세

  I.  스왑시장 동향

    당일 CD금리는 전 주 대비 상승하였다. IRS 금리는 전반적으로 상승하였고, CRS 금리도 대체로 상승 추세를 보였다.

그림1. 주요 금리 추이 (단위: %)
"""
IRS_PAGE, KTB_PAGE, CREDIT_PAGE = 5, 6, 3          # kis_pages()에서 표가 든 쪽의 차례


def kis_pages(issue="1212", date="2026-11-13", prev="2026-11-06", irs=IRS, crs=CRS, ktb=KTB, credit=None, extra=()):
    d = datetime.date.fromisoformat(date)
    cover = f"KIS WEEKLY                   {issue}호 {d.strftime('%Y.%m.%d')}\n\n PART  1 국내  / 해외채권\n"
    credit = credit if credit is not None else credit_block(f"{d.month}/{d.day}", f"{int(prev[5:7])}/{int(prev[8:])}")
    swap1 = swap_block(2, "KRW IRS Data", "KRW IRS", date, prev, irs) + "\n\n그림5. KRW CRS\n\n" + swap_block(3, "KRW CRS Data", "KRW CRS", date, prev, crs)
    swap2 = swap_block(4, "KTB Data", "URD IRS", date, prev, ktb) + "\n\n그림7. IRS 장단기 스프레드 추이\n"
    return [cover, EXEC, MARKET, CORP + credit + "\n\n                18\n", SWAP_HEAD, swap1, swap2, *extra]


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
KAP_SHORT = """Fixed Income Weekly

  주간 단기 금융시장 동향

  홍길동   대리  (1234-5678) someone@example.invalid
  김아무   연구원  (2345-6789) other@example.invalid

   ‘지어낸 CP 약세’

   지난 주 단기자금시장은 지어낸 적수 부족으로 시작하였으며 MMF 자금은 전전주 대비 감소하였음.

<그림>  지준  적수
자료: 한국자산평가
"""
KAP_KTB = """Fixed Income Weekly

  주간 국공채 시장동향

  박아무 연구원(1234-5670) p@example.invalid

  '지어낸 제목'

  바

  지난주 국내 채권 시장은 지어낸 물가 지표 상회로 약세를 보였음. 주 후반 지어낸 인사들의

  매파적 발언이 이어지며 약세 흐름을 이어갔음.

  0

  국고 3년 수익률은 전전주 대비 상승하였음.

<주간국채금리변동> (단위 : %, bp)
"""


def kap_pages(issue="26-46", month="November 16"):
    return [KAP_PAGE.replace("November 16, Vol.26-46", f"{month}, Vol.{issue}"), KAP_SHORT, KAP_KTB]


KIS_GOOD = {"국채": "국고 3년물이 한 주 사이 12.5bp 올라 국공채가 약세를 보였다. 지어낸 물가 지표가 예상치를 웃돈 영향이었다.",
            "크레딧": "회사채 금리가 모든 구간에서 올랐지만 단기 구간 스프레드는 좁혀졌다. 은행채도 스프레드가 줄며 강세였다.",
            "단기자금": None, "해외 금리": None,
            "스왑": "CD 91일물 금리가 0.03% 올랐고 IRS와 CRS 금리도 함께 상승했다."}
KAP_GOOD = {"국채": "지어낸 물가 지표가 예상보다 높게 나오고 매파적 발언이 겹치며 국채 금리가 크게 올라 약세가 이어졌다.",
            "크레딧": "크레딧 시장은 금리가 오른 데 따른 수요로 단기물이 강세였고 스프레드가 좁아졌다.",
            "단기자금": "연말 차환 부담과 수요 둔화가 겹치며 단기 금리 오름세가 계속됐다. MMF 자금은 줄었다.",
            "해외 금리": None}
COPIED = "주 첫 영업일 국내 채권시장은 지어낸 증시 호조에 약세로 출발했고 금리가 올랐다."      # KIS 글과 너무 비슷하다(copy)
KAP_COPIED = "지난주 국내 채권 시장은 지어낸 물가 지표 상회로 약세를 보였다."                     # KAP 글과 너무 비슷하다(copy)


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
    """가짜 응답 — read(n)은 이어 읽는다. on_read(번째)가 있으면 조각마다 부른다(느린 응답 흉내)."""

    def __init__(self, url, body, status=200, final=None, on_read=None):
        self.url, self.body, self.status, self.final, self.at, self.on_read, self.reads = url, body, status, final or url, 0, on_read, 0

    def read(self, n=-1):
        self.reads += 1
        if self.on_read:
            self.on_read(self.reads)
        n = len(self.body) - self.at if n < 0 else n
        out = self.body[self.at:self.at + n]
        self.at += len(out)
        return out

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
    """가짜 claude — 점검 호출에는 짧은 답, 본 호출에는 answer, 고쳐 쓰기 호출에는 repair(없으면 answer)를 JSON으로. 물은 보고서만 답한다.
    repair_code = 고쳐 쓰기 호출만의 종료코드. 부른 명령 · 표준입력을 적는다."""

    def __init__(self, answer=None, code=0, tools=(), tool_use=False, repair=None, repair_code=0):
        self.answer = {"kis": KIS_GOOD, "kap": KAP_GOOD} if answer is None else answer
        self.code, self.tools, self.tool_use, self.calls = code, list(tools), tool_use, []
        self.repair, self.repair_code = repair, repair_code

    def __call__(self, cmd, input=None, cwd=None, env=None, timeout=None, capture_output=None):
        text = input.decode("utf-8")
        self.calls.append(types.SimpleNamespace(cmd=list(cmd), text=text, cwd=cwd, env=dict(env or {}), timeout=timeout,
                                                empty=os.path.isdir(cwd) and not os.listdir(cwd)))
        probe, fix = text == L.PROBE, "고쳐 쓰기:" in text
        asked = set(re.findall(r"^보고서 (\w+) — ", text, flags=re.M))            # 물은 보고서만 답한다(묻지 않은 열쇠가 있으면 답 전체가 버려진다)
        answer = self.repair if fix and self.repair is not None else self.answer
        ans = '{"ok":true}' if probe else answer if isinstance(answer, str) else json.dumps(
            {k: v for k, v in answer.items() if k in asked}, ensure_ascii=False)
        init = {"type": "system", "subtype": "init", "tools": self.tools, "mcp_servers": [], "skills": [], "slash_commands": [],
                "model": "claude-fx-1"}
        blocks = [{"type": "text", "text": ans}] + ([{"type": "tool_use", "id": "t", "name": "Bash", "input": {}}] if self.tool_use else [])
        done = {"type": "result", "subtype": "success", "is_error": False, "result": ans,
                "usage": {"input_tokens": 100, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}
        out = "\n".join(json.dumps(e, ensure_ascii=False) for e in (init, {"type": "assistant", "message": {"content": blocks}}, done))
        return types.SimpleNamespace(returncode=self.repair_code if fix else self.code, stdout=out.encode("utf-8"), stderr=b"")

    def main_calls(self):
        return [c for c in self.calls if c.text != L.PROBE]

    def repair_calls(self):
        return [c for c in self.calls if "고쳐 쓰기:" in c.text]


def make_io(web=None, claude=None, table=None, today=TODAY, clock=None, ready=True):
    clock = clock or Clock()
    return {"run": claude or Claude(), "open": web or Web(site()), "sleep": clock.sleep, "clock": clock, "today": today,
            "pages": pages_of(table), "ready": lambda: ready, "tool": None, "python": sys.executable}


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
        self.assertEqual(F.KEYS["kis"][:9], F.KEYS["kap"])                          # KAP는 숫자 칸이 없다
        self.assertEqual((F.KIS_HOST, F.KAP_HOST), ("www.bond.co.kr", "www.koreaap.com"))
        self.assertTrue(all(u.startswith("https://") for u in (F.KIS_LIST, F.KIS_PDF, F.KAP_LIST, F.KAP_PDF, F.KAP_BOARD)))
        self.assertEqual((F.DUE_DAYS, F.RETRY_DAYS, F.TRIES), (6, 7, 3))
        self.assertEqual((F.TOPIC_MIN, F.TOPIC_TARGET, F.TOPIC_CHARS, F.TOPIC_SENTENCES, F.SUMMARY_MIN_TOPICS, F.TOPIC_NUMS), (20, 150, 230, 3, 2, 3))
        self.assertEqual(F.TOPICS_OF, {"kis": ("국채", "크레딧", "단기자금", "해외 금리", "스왑"), "kap": ("국채", "크레딧", "단기자금", "해외 금리")})
        self.assertEqual(F.COPY_STEMS, K.TH["copy_stems"] + 1)
        self.assertEqual(set(F.WHY), set(F.NOTES) - {"model", "none", "text"})       # 고쳐 쓰기의 까닭은 검사 사유마다 하나

    def test_frozen_shape_matches_the_evening_rules_today(self):
        # 굳힌 꼴은 2026-11-23의 저녁판 규칙과 같다 — 저녁판이 바뀌면 이 테스트가 알린다(굳힌 쪽은 그대로 두고 뜻한 변화인지 본다)
        self.assertEqual(F._CHARS.pattern, K._CHARS.pattern)
        self.assertEqual((F._END.pattern, F._DECIMAL.pattern, F._LINKISH.pattern, F._PHONE.pattern),
                         (K._END.pattern, K._DECIMAL.pattern, K._LINKISH.pattern, K._PHONE.pattern))
        self.assertEqual(F.HANGUL_MIN, K.TH["fact_hangul_min"])

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
        pages[IRS_PAGE] = pages[IRS_PAGE].replace("       주간증감     0.1", "       주간증감     0.2", 1)
        self.bad(pages)                                                               # 주간증감 ≠ 이번 주 − 지난주
        pages = kis_pages()
        pages[IRS_PAGE] = pages[IRS_PAGE].replace("연말대비", "연간대비", 1)
        self.bad(pages)                                                               # 모르는 줄
        self.bad(kis_pages()[:IRS_PAGE] + kis_pages()[IRS_PAGE + 1:])                  # IRS · CRS 쪽이 빠졌다
        pages = kis_pages()
        self.bad(pages + [pages[IRS_PAGE]])                                            # 같은 표가 둘 — 어느 것인지 모른다

    def test_january_issues_keep_their_numbers(self):
        # 1월 첫 호: 지난주가 지난해 12-30이면 날짜 크기로는 지난해 말보다 늦고, 12-31이면 두 날짜 줄이 같다 — 표의 차례로 읽는다
        for date, prev in (("2027-01-08", "2026-12-30"), ("2027-01-07", "2026-12-31"), ("2027-01-02", "2026-12-26")):
            with self.subTest(prev=prev):
                pages = kis_pages(date=date, prev=prev)
                if prev.endswith("12-31"):                                           # 지난주 = 지난해 말: 두 줄의 값도 같다
                    same = {k: (v[0], v[1], v[1]) for k, v in IRS.items()}
                    pages = kis_pages(date=date, prev=prev, irs=same, crs={k: (v[0], v[1], v[1]) for k, v in CRS.items()},
                                      ktb={k: (v[0], v[1], v[1]) for k, v in KTB.items()})
                n = F.kis_numbers(pages, date)
                self.assertEqual((n["date"], n["prev"]), (date, prev))
        self.bad_on([p.replace("2025-12-31", "2026-12-31") for p in kis_pages()], "2026-11-13")   # 지난해 말 줄이 지난해 것이 아니다

    def bad_on(self, pages, date):
        with self.assertRaises(F.Bad):
            F.kis_numbers(pages, date)

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
    def test_kis_sections_summary_page_and_section_bodies(self):
        secs = F.sections_of("kis", kis_pages())
        self.assertEqual([l for l, _ in secs], ["요약 쪽", "국공채", "회사채", "스왑"])          # 없는 절(금융채 · 단기사채 · 해외채권)은 빠진다
        head = secs[0][1].split("\n")
        self.assertEqual([x.split(":")[0] for x in head if not x.startswith("- ")], ["국공채", "금융채", "회사채", "CD/CP", "해외채권", "SWAP"])
        self.assertIn("해외채권: 지어낸 물가 우려에 미 국채금리 상승", head)            # 줄바꿈으로 이어진 제목
        self.assertIn("- CD : 감소, CD-은행채 스프레드 감소", head)
        body = dict(secs)
        self.assertTrue(body["국공채"].startswith("주 첫 영업일") and "금리가상승했다." in body["국공채"] and "12.5bp" in body["국공채"])
        self.assertTrue(body["국공채"].endswith("문의는 [메일]"))                          # 본문 줄의 전자우편은 가리기만 한다
        self.assertTrue(body["회사채"].startswith("회사채 3년 AA- 등급 스프레드는") and "표1" not in body["회사채"])
        self.assertTrue(body["스왑"].startswith("당일 CD금리는"))
        whole = "\n".join(t for _, t in secs)
        for gone in ("INDEX", "지수 누적수익률", "가나다라제일차", "ELS", "주가지수", "홍길동", "김아무", "이아무", "1234-56", "KEY POINT",
                     "평가담당자", "someone@", "그림1", "AAA", "URD"):
            self.assertNotIn(gone, whole)
        self.assertEqual(F.sections_of("kis", kis_pages()[2:]), [])                   # 요약 쪽이 없으면 묻지 않는다

    def test_kap_sections_drop_author_lines_and_scraps(self):
        secs = F.sections_of("kap", kap_pages())
        self.assertEqual([l for l, _ in secs], ["요약 쪽", "단기 금융시장", "국공채"])
        body = dict(secs)
        self.assertEqual(body["요약 쪽"].split("\n")[0], "지어낸 단기 금리는 연말 차환 부담과 수요 둔화로 오름세를 이어갔음.")
        self.assertEqual(len(body["요약 쪽"].split("\n")), 3)
        self.assertEqual(body["단기 금융시장"], "‘지어낸 CP 약세’ 지난 주 단기자금시장은 지어낸 적수 부족으로 시작하였으며 MMF 자금은 전전주 대비 감소하였음.")
        self.assertEqual(body["국공채"], "'지어낸 제목' 지난주 국내 채권 시장은 지어낸 물가 지표 상회로 약세를 보였음. 주 후반 지어낸 인사들의"
                                       "매파적 발언이 이어지며 약세 흐름을 이어갔음. 국고 3년 수익률은 전전주 대비 상승하였음.")   # '바' · '0' 줄은 건너뛴다
        whole = "\n".join(t for _, t in secs)
        for gone in ("수익률곡선", "4.700", "본보고서", "CONTACT", "홍길동", "김아무", "박아무", "someone@", "other@", "p@", "1234-5678",
                     "2345-6789", "대표전화", "<그림>", "자료:"):
            self.assertNotIn(gone, whole)
        no_caption = kap_pages()[0].replace("▲ 수익률곡선추이와장단기금리등락폭", "")
        t2 = F.kap_summary([no_caption])
        self.assertNotIn("4.700", t2)
        self.assertIn("크레딧 스프레드는축소되었음.", t2)
        self.assertEqual(F.sections_of("kap", ["Fixed Income Weekly\n본문만", KAP_SHORT]), [])
        dup = F.sections_of("kap", kap_pages() + [KAP_SHORT.replace("지어낸 적수", "다른 적수")])
        self.assertIn("지어낸 적수", dict(dup)["단기 금융시장"])                             # 같은 절이 둘이면 앞의 것

    def test_section_text_is_cut_at_a_sentence_end(self):
        long = "Fixed Income Weekly\n주간 국공채 시장동향\n" + "\n".join(["국고채 금리가 지어낸 까닭으로 올랐음." * 3] * 40) + "\n<표>\n"
        t = dict(F.sections_of("kap", kap_pages()[:1] + [long]))["국공채"]
        self.assertLessEqual(len(t), F.SECTION_MAX)
        self.assertTrue(t.endswith("음."))
        self.assertEqual(F._cut("가" * 1000), "가" * F.SECTION_MAX)                    # 마침표가 없으면 그냥 자른다

    def test_author_rule(self):
        for line in ("홍길동 대리 (1234-5678) someone@example.invalid", "김아무 연구원(2251-1466) k@example.invalid",
                     "평가담당자 KEY POINT", "홍길동 과장 02) 1234-5678 • 지어낸 요점"):
            self.assertTrue(F._author(line), line)
        prose = "상승했다. 국고 3년물은 지난주 대비 12.5bp 상승했고 국고 10년은 14.0bp 상승 마감했다. 문의는 someone@example.invalid 로 하면 된다고 적었다."
        self.assertGreater(len(prose), F.AUTHOR_LINE)
        self.assertFalse(F._author(prose))                                           # 긴 본문 줄은 담당자 줄이 아니다(가리기만 한다)
        self.assertFalse(F._author("지어낸 단기 금리는 오름세를 이어갔음."))
        self.assertEqual(F._mask("문의 02) 1234-5678 · (2283-3630) · a@b.co · https://x.example/y"), "문의 [전화] · [전화] · [메일] · [링크]")

    def test_cover_must_match_the_list(self):
        F.check_cover("kis", kis_pages(), {"issue": "1212", "date": "2026-11-13"})
        F.check_cover("kap", kap_pages(), {"issue": "26-46", "date": "2026-11-16"})
        F.check_cover("kap", kap_pages("26-45", "November 09"), {"issue": "26-45", "date": "2026-11-09"})
        for src, pages, item in (("kis", kis_pages(), {"issue": "1213", "date": "2026-11-13"}),
                                 ("kis", kis_pages(), {"issue": "1212", "date": "2026-11-12"}),
                                 ("kis", kis_pages(), {"issue": "12", "date": "2026-11-13"}),          # 호수의 끝만 맞는 것
                                 ("kis", kis_pages(), {"issue": "212", "date": "2026-11-13"}),
                                 ("kap", kap_pages(), {"issue": "26-45", "date": "2026-11-16"}),
                                 ("kap", kap_pages(), {"issue": "26-4", "date": "2026-11-16"}),        # 앞만 맞는 것
                                 ("kap", kap_pages(), {"issue": "26-46", "date": "2026-11-09"}),       # 표지 날짜가 다르다
                                 ("kap", [], {"issue": "26-46", "date": "2026-11-16"})):
            with self.subTest(item=item):
                self.assertRaises(F.Bad, F.check_cover, src, pages, item)


# ---------- 요약 검사 ----------

class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.kis = [t for _, t in F.sections_of("kis", kis_pages())]
        self.kap = [t for _, t in F.sections_of("kap", kap_pages())]

    def test_own_words_pass_topic_by_topic(self):
        for src, good, texts in (("kis", KIS_GOOD, self.kis), ("kap", KAP_GOOD, self.kap)):
            items, failed = F.judge_topics(src, good, texts)
            self.assertEqual(list(items), [t for t, v in good.items() if v])
            self.assertEqual(failed, {})                                              # null 주제는 걸린 것이 아니다

    def test_each_check(self):
        g = KIS_GOOD["국채"]
        cases = [("kis", None, "none"), ("kis", "짧다.", "shape"), ("kis", g + " 셋째 문장이다. 넷째 문장이다.", "shape"),
                 ("kis", g.replace("영향이었다.", "영향이었다"), "shape"), ("kis", "가" * 120 + "다. " + "나" * 110 + "다.", "shape"),
                 ("kis", g.replace("국공채가", "국공채가 \"크게\""), "shape"), ("kis", g + " www.example.com 이다.", "shape"),
                 ("kis", "국고 3년물이 12.5bp 올랐다. 앞으로 금리는 더 오를 것으로 보인다.", "banned"),
                 ("kis", "국고 3년물이 12.5bp 올라 국공채가 약세였다. 은행채는 매수 우위였다.", "banned"),
                 ("kis", COPIED, "copy"),
                 ("kis", "국고 3년물이 한 주 사이 13.5bp 올라 국공채가 약세를 보였다. 회사채는 커브가 평탄해졌다.", "number"),
                 ("kis", "국고 3년물이 12.5bp, 국고 10년은 14.0bp 올랐고 CD 91일물은 0.03% 올랐다. 스프레드는 0.7bp 줄었다.", "number"),  # 값 숫자 넷
                 ("kis", "국고 3년물이 한 주 사이 12.5bp 올라 국공채가 약세를 보였다. 기준금리는 동결됐다.", "term"),
                 ("kis", "국고 3년물이 한 주 사이 12.5bp 올라 국공채가 약세를 보였다. QQZ 쪽 영향이 컸다.", "name"),
                 ("kap", "국채 금리가 크게 올랐다. CD 91일물은 3.37%로 마감했다는 사실이 적혔다.", "number"),
                 ("kap", "지어낸 물가 지표 상회로 국채 금리가 크게 올랐다. 단기물은 1년 안팎이 강세였다.", "digits")]
        for src, s, want in cases:
            with self.subTest(s=s):
                self.assertEqual(F.topic_code(src, s, self.kis if src == "kis" else self.kap), want)

    def test_terms_from_one_section_are_enough(self):
        # 절을 서로 다른 채널로 보면 A · B급 낱말이 한 절에만 있을 때 걸린다 — 보고서 하나는 한 출처다
        s = "회사채 스프레드가 단기를 중심으로 강세를 보이며 좁혀졌다. 회사채 금리는 모든 구간에서 올랐다."
        self.assertIsNone(F.topic_code("kis", s, self.kis))

    def test_main_code_and_topic_judging(self):
        self.assertEqual(F.main_code([]), "none")
        self.assertEqual(F.main_code(["copy", "number", "copy"]), "copy")
        self.assertEqual(F.main_code(["number", "copy"]), "copy")                      # 같으면 NOTES 차례
        items, failed = F.judge_topics("kis", {**KIS_GOOD, "국채": COPIED, "해외 금리": "짧다."}, self.kis)
        self.assertEqual((list(items), failed), (["크레딧", "스왑"], {"국채": "copy", "해외 금리": "shape"}))

    def test_answers_are_read_strictly(self):
        L_ = L
        got = F.answers_of(json.dumps({"kis": {"국채": "가", "스왑": None}}), ["kis", "kap"])
        self.assertEqual(got, {"kis": {"국채": "가", "크레딧": None, "단기자금": None, "해외 금리": None, "스왑": None},
                               "kap": {"국채": None, "크레딧": None, "단기자금": None, "해외 금리": None}})
        self.assertEqual(F.answers_of('```json\n{"kap": null}\n```', ["kap"])["kap"]["국채"], None)
        for bad in ('{"kis": {"국채": 1}}', '{"kis": {"주가": "가"}}', '{"kap": {"스왑": "가"}}', '{"xx": {}}', '[]', 'not json',
                    '{"kis": "가"}', '{"kis": {"국채": "가", "국채": "나"}}'):
            with self.subTest(bad=bad), self.assertRaises(L_.Ask):
                F.answers_of(bad, ["kis", "kap"])

    def test_copy_rule_is_the_evening_one_with_six_stems(self):
        text = "가나 다라 마바 사아 자차 카타 파하 거너 더러"
        five = "가나 다라 마바 사아 자차 이야기는 다른 데로 흘렀다."
        six = "가나 다라 마바 사아 자차 카타 이야기는 다른 데로 흘렀다."
        self.assertFalse(K.ok_copy(five, [text]))                                    # 저녁판은 다섯 어절에서 걸린다
        self.assertTrue(F.ok_copy(five, [text]))
        self.assertFalse(F.ok_copy(six, [text]))

    def test_prompt_shape(self):
        asked = [{"key": "kis", "sections": F.sections_of("kis", kis_pages()), "numbers": True},
                 {"key": "kap", "sections": F.sections_of("kap", kap_pages()), "numbers": False}]
        p = F.prompt_of(asked, "ab" * 8)
        body = p.split("<<<자료 abababababababab 시작>>>\n")[1].split("\n<<<자료 abababababababab 끝>>>")[0]
        lines = body.split("\n")
        self.assertEqual(lines[0], "보고서 kis — 숫자 씀 — 주제: 국채, 크레딧, 단기자금, 해외 금리, 스왑")
        self.assertIn("보고서 kap — 숫자 없음 — 주제: 국채, 크레딧, 단기자금, 해외 금리", lines)
        heads = [x for x in lines if not x.startswith("| ")]
        self.assertEqual(heads, ["보고서 kis — 숫자 씀 — 주제: 국채, 크레딧, 단기자금, 해외 금리, 스왑", "[요약 쪽]", "[국공채]", "[회사채]", "[스왑]",
                                 "보고서 kap — 숫자 없음 — 주제: 국채, 크레딧, 단기자금, 해외 금리", "[요약 쪽]", "[단기 금융시장]", "[국공채]"])
        self.assertNotIn("고쳐 쓰기:", p)
        fix = F.prompt_of(asked, "cd" * 8, {"kap": {"국채": "copy"}})
        self.assertIn("고쳐 쓰기:", fix)
        self.assertIn("- 보고서 kap · 주제 국채: " + F.WHY["copy"], fix)
        self.assertLess(fix.index("<<<자료 cdcdcdcdcdcdcdcd 끝>>>"), fix.index("고쳐 쓰기:"))     # 걸린 까닭은 자료 경계 밖, 이 스크립트의 글


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
        item = lambda t, x: {"topic": t, "text": x}
        self.broken(lambda d: d["reports"][kis]["summary"][0].update(text="앞으로 금리는 오를 것으로 보인다는 말이 적혔다."))
        self.broken(lambda d: d["reports"][kap]["summary"][0].update(text="국채 금리가 3bp 올랐고 크레딧은 강세를 이어갔다."))
        self.broken(lambda d: d["reports"][kis].update(summary="한 덩어리 글은 이제 꼴이 아니다."))
        self.broken(lambda d: d["reports"][kis].update(summary=d["reports"][kis]["summary"][:1]))      # 주제가 둘보다 적다
        self.broken(lambda d: d["reports"][kis]["summary"].reverse())                                  # 주제 차례
        self.broken(lambda d: d["reports"][kis]["summary"].append(dict(d["reports"][kis]["summary"][0])))   # 같은 주제 둘
        self.broken(lambda d: d["reports"][kap]["summary"].append(item("스왑", "IRS와 CRS 금리가 함께 올랐다고 적었다.")))   # KAP에 없는 주제
        self.broken(lambda d: d["reports"][kis]["summary"][0].update(topic="주가"))
        self.broken(lambda d: d["reports"][kis]["summary"][0].update(extra=1))
        self.broken(lambda d: d["reports"][kis]["summary"][0].update(text="가" * 240 + "다."))
        self.broken(lambda d: d["reports"][kis].update(summary=None))                   # 사유 없는 빈 요약
        self.broken(lambda d: d["reports"][kis].update(summary=None, summary_note="model"))   # 모델 이름이 남았다
        self.broken(lambda d: d["reports"][kis].update(summary=None, summary_note="copy", model=None, summary_dropped=1))
        self.broken(lambda d: d["reports"][kis].update(summary_note="model"))
        self.broken(lambda d: d["reports"][kis].update(summary_dropped=-1))
        self.broken(lambda d: d["reports"][kis].update(summary_dropped=True))
        self.broken(lambda d: d["reports"][kis].update(summary_dropped=3))                # 남은 주제(5 − 3 실림)보다 많이 뺐다
        self.broken(lambda d: d["reports"][kis].pop("summary_dropped"))
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
        d["reports"][0].update(summary=self.doc["reports"][0]["summary"], summary_note=None, summary_dropped=2, model="m")
        F.validate(d, TODAY)

    def test_the_ci_check_does_not_lean_on_the_evening_word_list(self):
        # CI(DataFileTest)는 strict=False — 저녁판 금지 낱말이 나중에 늘어도 올라 있는 파일이 배포를 막지 않는다. 꼴은 그대로 본다
        d = json.loads(F.dump(self.doc))
        d["reports"][0]["summary"][0]["text"] = "앞으로 금리는 오를 것으로 보인다는 말이 적혔다."
        self.assertRaises(F.Bad, F.validate, d, TODAY)
        F.validate(d, TODAY, strict=False)
        d["reports"][0]["summary"][0]["text"] = "꼴이 아닌 글"
        self.assertRaises(F.Bad, F.validate, d, TODAY, strict=False)


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

    def test_reads_in_chunks_with_a_deadline(self):
        clock = Clock()
        big = b"y" * (F.CHUNK * 3 + 5)
        n = F.Net(Web({"https://www.bond.co.kr/big": big}), clock.sleep, clock)
        self.assertEqual(n.get("https://www.bond.co.kr/big", len(big)), big)        # 조각으로 나눠 읽어도 그대로
        with self.assertRaises(F.Fetch) as e:
            F.Net(Web({"https://www.bond.co.kr/big": big}), clock.sleep, clock).get("https://www.bond.co.kr/big", len(big) - 1)
        self.assertEqual(e.exception.code, "format")                                   # 크기 상한
        slow = Resp("https://www.bond.co.kr/slow", big, on_read=lambda k: setattr(clock, "t", clock.t + 50))   # 조각마다 50초 — 느린 응답
        n = F.Net(Web({"https://www.bond.co.kr/slow": slow}), clock.sleep, clock)
        with self.assertRaises(F.Fetch) as e:
            n.get("https://www.bond.co.kr/slow", len(big))
        self.assertEqual(e.exception.code, "budget")
        self.assertLessEqual(slow.reads, 3)                                            # 예산(120초)을 넘긴 뒤 더 읽지 않는다

    def test_pdf_pages_refuses_non_pdf_too_many_pages_and_slow_extraction(self):
        with self.assertRaises(F.Fetch) as e:
            F.pdf_pages(b"<html>")
        self.assertEqual(e.exception.code, "pdf")
        clock = Clock()

        class Page:
            def extract_text(self, extraction_mode=None):
                clock.t += 40
                return "쪽"

        class Reader:
            def __init__(self, stream):
                self.pages = [Page() for _ in range(count[0])]
        fake = types.ModuleType("pypdf")
        fake.PdfReader = Reader
        real = sys.modules.get("pypdf")
        sys.modules["pypdf"] = fake
        try:
            count = [2]
            self.assertEqual(F.pdf_pages(b"%PDF-x", clock), ["쪽", "쪽"])
            for n, code in ((F.PAGES_MAX + 1, "pdf"), (5, "pdf")):                   # 쪽이 너무 많다 · 글 뽑기가 PDF_S초를 넘는다
                count = [n]
                with self.assertRaises(F.Fetch) as e:
                    F.pdf_pages(b"%PDF-x", clock)
                self.assertEqual(e.exception.code, code)
        finally:
            if real is None:
                sys.modules.pop("pypdf", None)
            else:
                sys.modules["pypdf"] = real


# ---------- 한 번 돌기 ----------

def listed(good, src):
    """지어낸 답 {주제: 글 | None} → 실릴 꼴 [{topic, text}](주제 차례대로, null은 빠진다)."""
    return [{"topic": t, "text": good[t]} for t in F.TOPICS_OF[src] if good.get(t)]


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.exe = FakeExe(self).path

    def run_update(self, old=None, off=(), today=TODAY, state=None, web=None, claude=None, table=None, force=False, ready=True):
        self.web, self.claude = web or Web(site()), claude or Claude()
        self.state = {} if state is None else state
        io_ = make_io(self.web, self.claude, table, today, ready=ready)
        return F.update(old, set(off), today, io_, self.state, force=force, claude=self.exe)

    def test_first_run_fetches_both_and_asks_once(self):
        doc, seen = self.run_update()
        F.validate(doc, TODAY)
        kis, kap = doc["reports"]
        self.assertEqual((kis["issue"], kis["date"], kis["posted"], kis["url"]), ("1212", "2026-11-13", "2026-11-16", "https://www.bond.co.kr/post/dawn/37184"))
        self.assertEqual((kap["issue"], kap["date"], kap["url"]), ("26-46", "2026-11-16", F.KAP_BOARD))
        self.assertEqual((kis["summary"], kap["summary"], kis["model"]), (listed(KIS_GOOD, "kis"), listed(KAP_GOOD, "kap"), "claude-fx-1"))
        self.assertEqual((kis["summary_dropped"], kap["summary_dropped"]), (0, 0))
        self.assertEqual(kis["numbers"]["rows"]["irs_1y"], [3.1, 10.0])
        self.assertEqual(seen, {"kis": "new", "num": "ok", "kap": "new", "requests": 4, "sum": "ok", "drop": 0, "fix": 0})
        self.assertEqual(self.web.asked, ["https://www.bond.co.kr/", "https://www.bond.co.kr/post/dawn/37184", F.KAP_LIST, KAP_URL])
        self.assertEqual(len(self.claude.calls), 2)                                    # 점검 한 번 + 본 호출 한 번(걸린 주제가 없으면 고쳐 쓰기 없음)
        main = self.claude.main_calls()[0]
        self.assertTrue(main.empty)
        self.assertIn("보고서 kis — 숫자 씀 — 주제: 국채, 크레딧, 단기자금, 해외 금리, 스왑", main.text)
        self.assertIn("보고서 kap — 숫자 없음 — 주제: 국채, 크레딧, 단기자금, 해외 금리", main.text)
        marks = re.findall(r"<<<자료 ([0-9a-f]{16}) (시작|끝)>>>", main.text)
        self.assertEqual([m[1] for m in marks], ["시작", "끝"])
        body = main.text.split(f"<<<자료 {marks[0][0]} 시작>>>\n")[1].split(f"\n<<<자료 {marks[0][0]} 끝>>>")[0]
        self.assertTrue(all(x.startswith(("| ", "보고서 ", "[")) for x in body.split("\n")))
        for gone in ("홍길동", "김아무", "박아무", "1234-5678", "someone@", "other@", "글쓴이이름", "가나다라제일차"):
            self.assertNotIn(gone, main.text)
        self.assertEqual(self.state, {"kis": {"issue": "1212", "tries": 0, "day": "2026-11-17"},
                                      "kap": {"issue": "26-46", "tries": 0, "day": "2026-11-17"}})

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

    def test_a_failed_issue_is_downloaded_once_a_day(self):
        doc, _ = self.run_update()
        later, state = datetime.date(2026, 11, 23), {}
        web = lambda: Web(site(**{"https://www.bond.co.kr/": kis_main((("37300", "1213", "20261120", "2026.11.23"),)),
                                  "https://www.bond.co.kr/post/dawn/37300": KIS_PDF}))    # 표지가 맞지 않는 새 호
        _, seen = self.run_update(doc, today=later, web=web(), state=state)
        self.assertEqual((seen["kis"], state["kis"]), ("cover", {"issue": "1213", "tries": 0, "day": "2026-11-23"}))
        for _ in range(2):                                                             # 같은 날 23:30 · 다음 실행 — 목록만, PDF는 받지 않는다
            _, seen = self.run_update(doc, today=later, web=web(), state=state)
            self.assertEqual(seen["kis"], "later")
            self.assertNotIn("https://www.bond.co.kr/post/dawn/37300", self.web.asked)
        _, seen = self.run_update(doc, today=later + datetime.timedelta(days=1), web=web(), state=state)
        self.assertEqual(seen["kis"], "cover")                                         # 이튿날 한 번 더
        _, seen = self.run_update(doc, today=later, web=web(), state=state, force=True)
        self.assertEqual(seen["kis"], "cover")                                         # --force는 하루 한 번을 넘는다

    def test_without_pypdf_nothing_is_fetched(self):
        doc, seen = self.run_update(ready=False)
        self.assertEqual((seen["kis"], seen["kap"], seen["requests"], doc["reports"]), ("pypdf", "pypdf", 0, []))
        self.assertEqual(self.web.asked, [])

    def test_a_misread_table_drops_the_numbers_only(self):
        pages = kis_pages()
        pages[IRS_PAGE] = pages[IRS_PAGE].replace("주간증감", "주간 증감")
        doc, seen = self.run_update(table={**PAGES, KIS_PDF: pages})
        kis = doc["reports"][0]
        self.assertEqual((kis["numbers"], kis["numbers_note"], kis["summary"], seen["num"]), (None, "table", listed(KIS_GOOD, "kis"), "table"))
        F.validate(doc, TODAY)

    def test_numbers_out_of_the_file_range_drop_the_numbers_not_the_run(self):
        big = {k: v for k, v in CRS.items()}
        big["1Y"] = (5.95, 2.85, 2.20)                                                 # 주간 310bp — 표는 맞지만 파일의 범위(200bp) 밖
        doc, seen = self.run_update(table={**PAGES, KIS_PDF: kis_pages(crs=big)})
        self.assertEqual((doc["reports"][0]["numbers"], doc["reports"][0]["numbers_note"], seen["num"]), (None, "table", "table"))
        F.validate(doc, TODAY)

    def test_failed_topics_are_written_once_more(self):
        first = {"kis": {**KIS_GOOD, "국채": COPIED}, "kap": KAP_GOOD}
        fixed = Claude(answer=first, repair={"kis": {"국채": KIS_GOOD["국채"], "크레딧": "고쳐 쓰기에서 묻지 않은 주제는 버린다고 적었다."}})
        doc, seen = self.run_update(claude=fixed)
        self.assertEqual(doc["reports"][0]["summary"], listed(KIS_GOOD, "kis"))       # 묻지 않은 주제(크레딧)의 새 답은 버린다
        self.assertEqual((seen["fix"], seen["drop"], doc["reports"][0]["summary_dropped"]), (1, 0, 0))
        rep = fixed.repair_calls()
        self.assertEqual(len(rep), 1)
        self.assertIn("- 보고서 kis · 주제 국채: " + F.WHY["copy"], rep[0].text)
        self.assertNotIn("보고서 kap ·", rep[0].text)
        self.assertNotIn(COPIED, rep[0].text)                                          # 버린 글은 건네지 않는다
        self.assertEqual(len(fixed.calls), 3)                                          # 점검 · 본 · 고쳐 쓰기(점검은 한 번)
        still = Claude(answer=first, repair={"kis": {"국채": COPIED}})
        doc, seen = self.run_update(claude=still)
        self.assertEqual((seen["fix"], seen["drop"], doc["reports"][0]["summary_dropped"]), (0, 1, 1))
        self.assertEqual([x["topic"] for x in doc["reports"][0]["summary"]], ["크레딧", "스왑"])
        F.validate(doc, TODAY)
        down = Claude(answer=first, repair_code=1)                                     # 고쳐 쓰기가 실패해도 첫 답의 결과는 그대로
        doc, seen = self.run_update(claude=down)
        self.assertEqual((seen["fix"], seen["fix_ask"], seen["sum"], doc["reports"][0]["summary_dropped"]), (0, "exit", "ok", 1))

    def test_too_few_topics_means_no_summary(self):
        bad = Claude(answer={"kis": KIS_GOOD, "kap": {"국채": KAP_GOOD["국채"], "크레딧": KAP_COPIED, "단기자금": "짧다.", "해외 금리": "짧다."}},
                     repair={"kap": {"크레딧": KAP_COPIED, "단기자금": "짧다.", "해외 금리": "짧다."}})
        doc, seen = self.run_update(claude=bad)
        kap = doc["reports"][1]
        self.assertEqual((kap["summary"], kap["summary_note"], kap["summary_dropped"], kap["model"]), (None, "shape", 0, None))
        self.assertEqual((seen["sum"], self.state["kap"]["tries"]), ("ok_shape", 1))
        doc, seen = self.run_update(claude=Claude(answer={"kis": KIS_GOOD, "kap": {}}))
        self.assertEqual((doc["reports"][1]["summary_note"], self.state["kap"]["tries"]), ("none", 1))   # 모두 null도 한 번으로 센다
        F.validate(doc, TODAY)

    def test_model_failure_keeps_the_entry_without_summary_and_retries(self):
        doc, seen = self.run_update(claude=Claude(code=1))
        self.assertEqual([(r["summary"], r["summary_note"], r["model"]) for r in doc["reports"]], [(None, "model", None)] * 2)
        self.assertEqual((seen["sum"], seen["ask"]), ("model", "exit"))
        self.assertEqual([self.state[k]["tries"] for k in ("kis", "kap")], [0, 0])     # 모델 실패는 셈하지 않는다
        F.validate(doc, TODAY)
        again, seen = self.run_update(doc, today=datetime.date(2026, 11, 18))           # 게시 뒤 7일 안 — 다시 받고 다시 묻는다
        self.assertEqual((seen["kis"], seen["kap"], seen["sum"]), ("retry", "retry", "ok"))
        self.assertEqual(again["reports"][0]["summary"], listed(KIS_GOOD, "kis"))
        _, seen = self.run_update(doc, today=datetime.date(2026, 11, 23))               # 7일이 지나면 다시 묻지 않는다(새 호를 기다린다)
        self.assertEqual((seen["kis"], seen["kap"]), ("same", "same"))
        for claude, code in ((Claude(tools=["Bash"]), "tools"), (Claude(tool_use=True), "tool_use"), (Claude(answer="not json"), "json")):
            _, seen = self.run_update(claude=claude)
            self.assertEqual((seen["sum"], seen["ask"]), ("model", code))

    def test_checked_out_answers_count_up_to_three_tries(self):
        bad = Claude(answer={"kis": {"국채": COPIED}, "kap": KAP_GOOD}, repair={"kis": {"국채": COPIED}})
        doc, seen = self.run_update(claude=bad)
        self.assertEqual((doc["reports"][0]["summary_note"], seen["sum"]), ("copy", "copy_ok"))
        self.assertEqual(self.state["kis"], {"issue": "1212", "tries": 1, "day": "2026-11-17"})
        state = self.state
        for n, day in ((2, 18), (3, 19)):                                              # 하루 한 번씩 다시
            doc, seen = self.run_update(doc, state=state, claude=bad, today=datetime.date(2026, 11, day))
            self.assertEqual((seen["kis"], seen["kap"], state["kis"]["tries"]), ("retry", "wait", n))
        _, seen = self.run_update(doc, state=state, claude=bad, today=datetime.date(2026, 11, 20))
        self.assertEqual((seen["kis"], seen["requests"]), ("wait", 0))                 # 세 번 걸렸으면 새 호까지 기다린다

    def test_force_and_short_text(self):
        doc, _ = self.run_update()
        _, seen = self.run_update(doc, today=datetime.date(2026, 11, 18), force=True)
        self.assertEqual((seen["kis"], seen["kap"]), ("retry", "retry"))
        table = {**PAGES, KAP_PDF: [kap_pages()[0].split("▲")[0] + "▲ 그림\n짧은 글만 있다.\n본보고서는 x"]}
        doc, seen = self.run_update(table=table)
        self.assertEqual((doc["reports"][1]["summary_note"], seen["sum"]), ("text", "ok"))   # 묻지 않았다
        self.assertNotIn("보고서 kap", self.claude.main_calls()[0].text)
        self.assertEqual(self.state["kap"]["tries"], 1)                                # 읽힐 글이 없던 것도 한 번


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


def plant_script(repo):
    """게시 전용 폴더의 main 끝에 이 게시기가 있다(없으면 gone으로 멈춘다)."""
    os.makedirs(os.path.join(repo, "scripts"), exist_ok=True)
    open(os.path.join(repo, "scripts", "fi_weekly.py"), "w").close()


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, True)
        plant_script(self.repo)
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
        self.assertEqual(F.publish(self.repo, self.doc, TODAY, t, recheck=lambda: set()), "pushed")
        self.assertEqual(t.names().count("push"), 2)
        self.assertEqual(t.names().count("checkout"), 1)

    def retry(self, checkout, recheck=lambda: set(), had=False):
        """push가 거절되고 main이 움직인 경우 — checkout(새 main의 끝으로)이 폴더를 바꾼다."""
        file = os.path.join(self.repo, *PATH.split("/"))
        if had:
            F._write(self.repo, F.dump(F.empty(datetime.date(2026, 11, 10))))      # main에 옛 파일이 있었다
        heads = iter(["aaa\naaa\n", "bbb\n"])
        t = good_tool(status=(0, MOD if had else NEW), push=[1, 0], rev_parse=lambda c: (0, next(heads)),
                      checkout=lambda c: (checkout(file), 0)[1])
        with self.assertRaises(F.Stop) as e:
            F.publish(self.repo, self.doc, TODAY, t, recheck=recheck)
        self.assertEqual(t.names().count("push"), 1)                                   # 다시 올리지 않는다
        return e.exception.code

    def test_the_retry_does_not_undo_a_takedown(self):
        # 그사이 main에서 파일을 지웠다 / 스위치로 내렸다 / 게시기를 지웠다 — 옛 바이트를 새 main에 올리지 않는다
        self.assertEqual(self.retry(lambda f: os.remove(f), had=True), "moved")
        self.assertEqual(self.retry(lambda f: os.remove(f), recheck=lambda: {"kap"}), "moved")
        self.assertEqual(self.retry(lambda f: (os.remove(f), os.remove(os.path.join(self.repo, "scripts", "fi_weekly.py")))), "gone")

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
        plant_script(self.repo)
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
        names = tool.names()
        self.assertEqual(names[0], "status")                                          # sync가 먼저(잔재를 치운다) → 그다음 스위치
        self.assertLess(names.index("checkout"), names.index("gh"))
        state = os.path.join(self.repo, ".work", "fi_weekly", "state.json")
        self.assertTrue(os.path.exists(state))
        F._write(self.repo, b"{}")                                                    # 앞 실행이 끊겨 남긴 파일
        tool = self.tool(gh=(1, ""))
        code, out = self.main(tool=tool)
        self.assertEqual(code, 2)
        self.assertIn("code=switch", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, *PATH.split("/"))))   # 스위치를 못 읽어도 잔재는 치웠다
        os.remove(state)
        tool = self.tool(blind=1)
        code, out = self.main(tool=tool)
        self.assertEqual(code, 2)
        self.assertIn("code=blind", out)
        self.assertIn(["git", "reset", "--quiet", "--", PATH], tool.calls)            # 멈추면 정리한다(tidy)
        self.assertFalse(os.path.exists(os.path.join(self.repo, *PATH.split("/"))))
        with open(state, encoding="utf-8") as f:                                     # 멈췄어도 오늘 받은 호를 남긴다 — 같은 날 다시 받지 않게
            self.assertEqual({k: v["day"] for k, v in json.load(f).items()}, {"kis": "2026-11-17", "kap": "2026-11-17"})
        web = Web(site())
        code, out = self.main(tool=self.tool(blind=1), web=web)
        self.assertIn("kis=later", out)
        self.assertNotIn("https://www.bond.co.kr/post/dawn/37184", web.asked)

    def test_a_removed_publisher_does_nothing(self):
        os.remove(os.path.join(self.repo, "scripts", "fi_weekly.py"))                 # main에서 칸 전체를 내렸다(옛 코드가 돈다)
        web, claude = Web(site()), Claude()
        code, out = self.main(web=web, claude=claude)
        self.assertEqual(code, 2)
        self.assertIn("code=gone", out)
        self.assertEqual((web.asked, claude.calls), ([], []))
        self.assertFalse(os.path.exists(os.path.join(self.repo, *PATH.split("/"))))

    def test_tidy_mode_only_puts_the_file_back(self):
        F._write(self.repo, b"{}")
        tool, web = self.tool(), Web(site())
        code, out = self.main(["--tidy"], tool=tool, web=web)
        self.assertEqual(code, 0)
        self.assertIn("result=tidy", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, *PATH.split("/"))))
        self.assertEqual(web.asked, [])
        self.assertNotIn("gh", tool.names())

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
        os.makedirs(os.path.join(self.other, "scripts"))
        for name, body in (("data/digest_picks.json", "{}"), ("data/people_remarks.json", "{}"), (".gitignore", ".work/\n"),
                           ("scripts/fi_weekly.py", "# 자리\n")):
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

    def test_taking_the_card_down_as_the_readme_says(self):
        self.assertEqual(self.run_main(), 0)
        self.git(self.other, "pull", "--quiet", "--rebase", "origin", "main")
        self.git(self.other, "rm", "--quiet", PATH, "scripts/fi_weekly.py")           # 운영자가 main에서 둘을 함께 지운다
        self.git(self.other, "commit", "--quiet", "-m", "take down")
        self.git(self.other, "push", "--quiet", "origin", "HEAD:main")
        before = self.git(self.other, "rev-parse", "HEAD").strip()
        self.assertEqual(self.run_main(datetime.datetime(2026, 11, 24, 17, 45, tzinfo=KST)), 2)   # 지우기 전의 코드가 돌아도 다시 올리지 않는다
        self.git(self.other, "fetch", "--quiet", "origin", "main")
        self.assertEqual(self.git(self.other, "rev-parse", "origin/main").strip(), before)
        self.assertEqual(self.status(), "")


# ---------- 올라 있는 파일 · 화면 · 문서 ----------

@unittest.skipUnless(os.path.exists(DATA_FILE), "data/fi_weekly.json이 아직 없다")
class DataFileTest(unittest.TestCase):
    """올라 있는 공개 파일을 게시기와 같은 검사로 — 손으로 고쳐 깨뜨린 파일이 배포되지 않게(CI의 check가 배포 앞에서 돈다)."""

    def test_published_file_follows_the_contract(self):
        with open(DATA_FILE, "rb") as f:
            raw = f.read()
        doc = F.validate(json.loads(raw.decode("utf-8")), datetime.date.today(), strict=False)   # 저녁판 낱말 목록에 기대지 않는다
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
        topics = pick("TOPICS")
        self.assertEqual({k: tuple(re.findall(r'"([^"]+)"', topics[topics.index(k + ":"):].split("]")[0])) for k in F.SOURCES}, F.TOPICS_OF)
        self.assertIn(f"const TOPIC_CHARS = {F.TOPIC_CHARS}, MIN_TOPICS = {F.SUMMARY_MIN_TOPICS};", js)
        self.assertIn(f'const KAP_BOARD = "{F.KAP_BOARD}";', js)
        self.assertIn(r"const KIS_ITEM = /^https:\/\/www\.bond\.co\.kr\/post\/dawn\/[0-9]{1,9}$/;", js)
        self.assertIn('doc.schema !== "' + F.SCHEMA + '"', js)
        self.assertIn("x.text.length > TOPIC_CHARS", js)
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
        self.assertIn("$w.WaitForExit(900000)", code)                                 # 15분 — 넘으면 멈추고 --tidy로 정리만
        self.assertIn('Start-Process -FilePath $py -ArgumentList ($fiArgs + @("--tidy"))', code)
        self.assertNotIn("-Wait -PassThru", code)
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
